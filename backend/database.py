import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                if self.db_name == "wallets.db":
                    c.execute('''CREATE TABLE IF NOT EXISTS wallets (
                        user_id TEXT PRIMARY KEY,
                        wallet_address TEXT,
                        nonce INTEGER DEFAULT 0
                    )''')
                    # Bảng mới để theo dõi vị thế yield farming
                    c.execute('''CREATE TABLE IF NOT EXISTS positions (
                        position_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        platform TEXT,  -- "aave" hoặc "uniswap"
                        initial_amount REAL,  -- Số tiền ban đầu (USDC hoặc LP token)
                        initial_value_usd REAL,  -- Giá trị USD ban đầu
                        start_time INTEGER,  -- Timestamp bắt đầu
                        status TEXT DEFAULT 'active',  -- "active" hoặc "closed"
                        FOREIGN KEY (user_id) REFERENCES wallets(user_id)
                    )''')
                elif self.db_name == "credits.db":
                    c.execute('''CREATE TABLE IF NOT EXISTS credits (
                        user_id TEXT PRIMARY KEY,
                        credits INTEGER DEFAULT 0
                    )''')
                conn.commit()
                logger.info(f"Initialized database: {self.db_name}")
        except Exception as e:
            logger.error(f"Failed to initialize database {self.db_name}: {str(e)}")
            raise

    def execute(self, query: str, params: tuple = ()):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute(query, params)
                conn.commit()
                return c.lastrowid
        except Exception as e:
            logger.error(f"Database error in {self.db_name}: {str(e)}")
            raise

    def fetch_one(self, query: str, params: tuple = ()):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute(query, params)
                return c.fetchone()
        except Exception as e:
            logger.error(f"Database fetch error in {self.db_name}: {str(e)}")
            raise

    def fetch_all(self, query: str, params: tuple = ()):  # Thêm hàm fetch_all
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute(query, params)
                return c.fetchall()
        except Exception as e:
            logger.error(f"Database fetch_all error in {self.db_name}: {str(e)}")
            raise
