from flask import Flask, render_template_string, request, abort, redirect, url_for
import sqlite3

ADMIN_PASSWORD = "nikita_lee"
DB_PATH = "lucifer_bot.db"

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Админ-панель LuciferBot</title>
  <style>
    body { font-family: sans-serif; background: #111; color: #eee; padding: 2em; }
    h1, h2 { color: #0f0; }
    table { width: 100%; border-collapse: collapse; margin: 1em 0; }
    th, td { padding: 0.5em; border: 1px solid #444; }
    th { background: #222; }
    a, a:visited { color: #6cf; }
    form { margin-top: 2em; }
    input[type="submit"], button { padding: 0.3em 1em; background: #222; color: #fff; border: 1px solid #555; cursor: pointer; }
    input[type="text"], input[type="number"] { padding: 0.2em; width: 100%; }
  </style>
</head>
<body>
  <h1>🏆 NFT Рейтинг</h1>
  <table>
    <tr><th>#</th><th>Ник</th><th>Кол-во</th><th>Сумма</th><th>Предметы</th><th>Удалить</th></tr>
    {% for row in data %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>@{{ row["username"] or "без ника" }}</td>
      <td>{{ row["count"] }}</td>
      <td>{{ row["total_cost"] }}</td>
      <td>{{ row["items"] }}</td>
      <td>
        <form method="post" action="/delete_user">
          <input type="hidden" name="username" value="{{ row['username'] }}">
          <input type="submit" value="Удалить">
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>

  <h2>📊 Статистика</h2>
  <table>
    <tr><th>Пользователей</th><th>Общий баланс</th><th>Транзакций</th></tr>
    <tr>
      <td>{{ stats.total_users }}</td>
      <td>{{ stats.total_balance or 0 }}</td>
      <td>{{ stats.total_transactions }}</td>
    </tr>
  </table>

  <form method="post" action="/reset_users">
    <h3>⚠️ Удалить всех пользователей (кроме system)</h3>
    <input type="submit" value="Удалить всех">
  </form>

  <h2>🎁 Добавить приз</h2>
  <form method="post" action="/add_prize">
    <input type="text" name="name" placeholder="Название" required>
    <input type="number" name="cost" placeholder="Цена" required>
    <input type="text" name="description" placeholder="Описание" required>
    <input type="number" name="stock" placeholder="Количество (-1 для беск.)" required>
    <label><input type="checkbox" name="is_nft" checked> NFT</label>
    <input type="submit" value="Добавить">
  </form>

  <h2>📥 Экспорт CSV</h2>
  <form method="get" action="/export">
    <input type="submit" value="Скачать CSV">
  </form>
</body>
</html>
"""

@app.before_request
def restrict():
    if request.args.get("password") != ADMIN_PASSWORD:
        abort(403)

@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    nft_query = """
        SELECT 
            u.username,
            COUNT(ui.prize_id) AS count,
            GROUP_CONCAT(p.name, ', ') AS items,
            SUM(p.cost) AS total_cost
        FROM user_items ui
        JOIN users u ON u.user_id = ui.user_id
        JOIN prizes p ON p.prize_id = ui.prize_id
        WHERE p.is_nft = 1
        GROUP BY ui.user_id
        ORDER BY total_cost DESC
        LIMIT 20;
    """
    rows = conn.execute(nft_query).fetchall()

    stats = conn.execute("""
        SELECT 
            (SELECT COUNT(*) FROM users),
            (SELECT SUM(balance) FROM users),
            (SELECT COUNT(*) FROM transactions)
    """).fetchone()

    return render_template_string(HTML, data=rows, stats={"total_users": stats[0], "total_balance": stats[1], "total_transactions": stats[2]})

@app.route("/reset_users", methods=["POST"])
def reset_users():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE user_id != 0")
    conn.commit()
    return redirect(url_for("index", password=ADMIN_PASSWORD))

@app.route("/delete_user", methods=["POST"])
def delete_user():
    username = request.form.get("username")
    if username:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    return redirect(url_for("index", password=ADMIN_PASSWORD))

@app.route("/add_prize", methods=["POST"])
def add_prize():
    name = request.form.get("name")
    cost = int(request.form.get("cost"))
    desc = request.form.get("description")
    stock = int(request.form.get("stock"))
    is_nft = 1 if request.form.get("is_nft") else 0

    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO prizes (name, cost, description, stock, is_nft) VALUES (?, ?, ?, ?, ?)",
                 (name, cost, desc, stock, is_nft))
    conn.commit()
    return redirect(url_for("index", password=ADMIN_PASSWORD))

@app.route("/export")
def export():
    import csv
    from io import StringIO
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM users").fetchall()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(rows[0].keys())
    for row in rows:
        writer.writerow(row)
    return output.getvalue(), 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=users.csv"
    }

if __name__ == "__main__":
    app.run(port=5000, debug=False)
