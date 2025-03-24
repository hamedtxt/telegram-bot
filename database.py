import sqlite3
from datetime import datetime, timedelta
import logging

class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.create_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        return conn

    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY_KEY,
                authority TEXT,
                subscription_end INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                message_id INTEGER PRIMARY_KEY,
                chat_id TEXT,
                text TEXT,
                file_id TEXT,
                tags TEXT,
                timestamp INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def add_user(self, user_id, authority, duration):
        conn = self.get_connection()
        cursor = conn.cursor()
        current_time = datetime.now()
        logging.info(f"زمان فعلی برای کاربر {user_id}: {current_time.timestamp()}")
        subscription_end = int((current_time + timedelta(days=duration)).timestamp())
        logging.info(f"پایان اشتراک برای کاربر {user_id}: {subscription_end}")
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, authority, subscription_end)
            VALUES (?, ?, ?)
        ''', (user_id, authority, subscription_end))
        conn.commit()
        conn.close()

    def get_user_by_authority(self, authority):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE authority = ?', (authority,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def is_vip(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            subscription_end = result[0]
            current_time = int(datetime.now().timestamp())
            logging.info(f"چک VIP برای کاربر {user_id}: subscription_end={subscription_end}, current_time={current_time}")
            return subscription_end > current_time
        logging.info(f"کاربر {user_id} توی دیتابیس پیدا نشد")
        return False

    def add_product(self, message_id, chat_id, text, file_id, tags):
        conn = self.get_connection()
        cursor = conn.cursor()
        timestamp = int(datetime.now().timestamp())
        tags_str = ','.join(tags)
        cursor.execute('''
            INSERT OR REPLACE INTO products (message_id, chat_id, text, file_id, tags, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_id, chat_id, text, file_id, tags_str, timestamp))
        conn.commit()
        conn.close()

    def get_product(self, message_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE message_id = ?', (message_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def get_all_products(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products')
        result = cursor.fetchall()
        conn.close()
        return result

    def close(self):
        pass