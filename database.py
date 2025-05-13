import sqlite3
from config import Config


class Database:
    _instance = None

    def register_user(self, user_id: int, username: str):
        self.execute(
            "INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0)",
            (user_id, username)
        )

    def _init_db(self):
        ...
        self.conn.executescript("""
            ...
            CREATE TABLE IF NOT EXISTS user_items (
                user_id INTEGER,
                prize_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id),
                PRIMARY KEY (user_id, prize_id)
            );
        """)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
            cls._instance.conn.row_factory = sqlite3.Row
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        with self.conn:
            self.conn.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0 NOT NULL CHECK(balance >= 0),
                    last_daily TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS prizes (
                    prize_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    cost INTEGER NOT NULL CHECK(cost > 0),
                    description TEXT,
                    stock INTEGER DEFAULT -1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user INTEGER REFERENCES users(user_id),
                    to_user INTEGER REFERENCES users(user_id),
                    amount INTEGER NOT NULL CHECK(amount > 0),
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    note TEXT
                );

                CREATE TABLE IF NOT EXISTS user_items (
                    user_id INTEGER,
                    prize_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(prize_id) REFERENCES prizes(prize_id),
                    PRIMARY KEY (user_id, prize_id)
                );
            """)
            # Добавляем системного пользователя для транзакций
            self.conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, is_admin) VALUES (0, 'system', 1);"
            )

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(query, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def get_user(self, user_id: int):
        return self.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def update_balance(self, user_id: int, amount: int):
        self.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.commit()

    def add_transaction(self, from_user: int, to_user: int, amount: int, note: str = None):
        self.execute(
            """INSERT INTO transactions 
            (from_user, to_user, amount, note) 
            VALUES (?, ?, ?, ?)""",
            (from_user, to_user, amount, note)
        )
        self.commit()

    def get_prizes(self):
        return self.execute("SELECT * FROM prizes").fetchall()

    def add_prize(self, name: str, cost: int, description: str, stock: int):
        self.execute(
            """INSERT INTO prizes (name, cost, description, stock)
            VALUES (?, ?, ?, ?)""",
            (name, cost, description, stock)
        )
        self.commit()

    def get_stats(self):
        return self.execute("""
            SELECT 
                COUNT(*) as total_users,
                SUM(balance) as total_balance,
                (SELECT COUNT(*) FROM transactions) as total_transactions
            FROM users
        """).fetchone()

    def buy_prize(self, user_id: int, prize_id: int):
        prize = self.execute("SELECT * FROM prizes WHERE prize_id = ?", (prize_id,)).fetchone()
        user = self.get_user(user_id)
        if not prize or user['balance'] < prize['cost']:
            return False, "Недостаточно средств или приз не найден"

        if prize['stock'] == 0:
            return False, "Приз закончился"

        with self.conn:
            self.update_balance(user_id, -prize['cost'])
            self.execute("INSERT OR IGNORE INTO user_items (user_id, prize_id) VALUES (?, ?)", (user_id, prize_id))
            if prize['stock'] > 0:
                self.execute("UPDATE prizes SET stock = stock - 1 WHERE prize_id = ?", (prize_id,))
            self.add_transaction(user_id, 0, prize['cost'], f"Покупка приза: {prize['name']}")
        return True, f"✅ Вы купили: {prize['name']}"

    def get_user_items(self, user_id: int):
        return self.execute("""
            SELECT p.name, p.cost, p.description FROM user_items ui
            JOIN prizes p ON p.prize_id = ui.prize_id
            WHERE ui.user_id = ?
        """, (user_id,)).fetchall()
db = Database()
