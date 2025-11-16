"""
Veritabanı Yönetim Modülü
SQLite kullanarak kullanıcı ve transaction verilerini yönetir
"""

import sqlite3
import os
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "data/investxxx.db"):
        """Veritabanı bağlantısını başlat"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Veritabanı bağlantısı al"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Dict-like row access
        return conn
    
    def init_database(self):
        """Veritabanı tablolarını oluştur"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Kullanıcılar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Transaction'lar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Portföy tablosu (kullanıcı bazında)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                cash REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Portföy hisseleri tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_cost REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                UNIQUE(portfolio_id, symbol)
            )
        """)
        
        # Index'ler
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(symbol)")
        
        conn.commit()
        conn.close()
        logger.info("Veritabanı tabloları oluşturuldu/doğrulandı")
    
    # === KULLANICI İŞLEMLERİ ===
    
    def create_user(self, username: str, password: str, email: str = None) -> Optional[int]:
        """Yeni kullanıcı oluştur"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email)
                VALUES (?, ?, ?)
            """, (username, password_hash, email))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Kullanıcı için boş portföy oluştur
            cursor.execute("""
                INSERT INTO portfolios (user_id, cash)
                VALUES (?, 0)
            """, (user_id,))
            conn.commit()
            
            logger.info(f"Yeni kullanıcı oluşturuldu: {username} (ID: {user_id})")
            return user_id
        except sqlite3.IntegrityError:
            logger.warning(f"Kullanıcı zaten mevcut: {username}")
            return None
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Kullanıcı doğrulama"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, is_active
            FROM users
            WHERE username = ? AND password_hash = ? AND is_active = 1
        """, (username, password_hash))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Son giriş zamanını güncelle
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (row['id'],))
            conn.commit()
            conn.close()
            
            return {
                'id': row['id'],
                'username': row['username'],
                'email': row['email'],
                'is_active': row['is_active']
            }
        
        return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Kullanıcı bilgilerini al"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, created_at, last_login, is_active
            FROM users
            WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'username': row['username'],
                'email': row['email'],
                'created_at': row['created_at'],
                'last_login': row['last_login'],
                'is_active': row['is_active']
            }
        
        return None
    
    # === TRANSACTION İŞLEMLERİ ===
    
    def add_transaction(self, user_id: int, transaction: Dict) -> int:
        """Yeni transaction ekle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transactions (user_id, type, symbol, quantity, price, total_value, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            transaction['type'],
            transaction['symbol'],
            transaction['quantity'],
            transaction['price'],
            transaction['total_value'],
            transaction['date']
        ))
        
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Transaction eklendi: {transaction_id} (User: {user_id})")
        return transaction_id
    
    def get_user_transactions(self, user_id: int, limit: int = None) -> List[Dict]:
        """Kullanıcının transaction'larını al"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, type, symbol, quantity, price, total_value, date, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        transactions = []
        for row in rows:
            transactions.append({
                'id': row['id'],
                'type': row['type'],
                'symbol': row['symbol'],
                'quantity': row['quantity'],
                'price': row['price'],
                'total_value': row['total_value'],
                'date': row['date'],
                'created_at': row['created_at']
            })
        
        return transactions
    
    def delete_transaction(self, user_id: int, transaction_id: int) -> bool:
        """Transaction sil"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM transactions
            WHERE id = ? AND user_id = ?
        """, (transaction_id, user_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"Transaction silindi: {transaction_id} (User: {user_id})")
        
        return deleted
    
    def remove_duplicate_transactions(self, user_id: int) -> int:
        """Kullanıcının duplicate transaction'larını temizle (aynı type, symbol, quantity, price, date olanlar)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Duplicate'leri bul (aynı type, symbol, quantity, price, date olanlar)
        cursor.execute("""
            SELECT type, symbol, quantity, price, date, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM transactions
            WHERE user_id = ?
            GROUP BY type, symbol, quantity, price, date
            HAVING COUNT(*) > 1
        """, (user_id,))
        
        duplicates = cursor.fetchall()
        total_deleted = 0
        
        for dup in duplicates:
            ids = [int(id_str) for id_str in dup['ids'].split(',')]
            # En eski ID'yi tut, diğerlerini sil
            ids_sorted = sorted(ids)
            keep_id = ids_sorted[0]  # En eski ID'yi tut
            delete_ids = ids_sorted[1:]  # Diğerlerini sil
            
            for delete_id in delete_ids:
                cursor.execute("""
                    DELETE FROM transactions
                    WHERE id = ? AND user_id = ?
                """, (delete_id, user_id))
                total_deleted += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if total_deleted > 0:
            logger.info(f"{total_deleted} duplicate transaction silindi (User: {user_id})")
        
        return total_deleted
    
    def check_transaction_exists(self, user_id: int, transaction: Dict) -> bool:
        """Transaction'ın zaten var olup olmadığını kontrol et"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM transactions
            WHERE user_id = ? 
            AND type = ?
            AND symbol = ?
            AND quantity = ?
            AND price = ?
            AND date = ?
        """, (
            user_id,
            transaction['type'],
            transaction['symbol'],
            transaction['quantity'],
            transaction['price'],
            transaction['date']
        ))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] > 0
    
    # === PORTFÖY İŞLEMLERİ ===
    
    def get_user_portfolio(self, user_id: int) -> Dict:
        """Kullanıcının portföyünü al"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Portföy bilgisi
        cursor.execute("""
            SELECT id, cash, updated_at
            FROM portfolios
            WHERE user_id = ?
        """, (user_id,))
        
        portfolio_row = cursor.fetchone()
        
        if not portfolio_row:
            # Portföy yoksa oluştur
            cursor.execute("""
                INSERT INTO portfolios (user_id, cash)
                VALUES (?, 0)
            """, (user_id,))
            portfolio_id = cursor.lastrowid
            cash = 0
            conn.commit()
        else:
            portfolio_id = portfolio_row['id']
            cash = portfolio_row['cash']
        
        # Hisseler
        cursor.execute("""
            SELECT symbol, quantity, avg_cost
            FROM portfolio_stocks
            WHERE portfolio_id = ?
        """, (portfolio_id,))
        
        stocks = {}
        for row in cursor.fetchall():
            stocks[row['symbol']] = {
                'quantity': row['quantity'],
                'avg_cost': row['avg_cost']
            }
        
        conn.close()
        
        return {
            'cash': cash,
            'stocks': stocks
        }
    
    def update_user_portfolio(self, user_id: int, portfolio: Dict):
        """Kullanıcının portföyünü güncelle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Portföy ID'sini al veya oluştur
        cursor.execute("""
            SELECT id FROM portfolios WHERE user_id = ?
        """, (user_id,))
        
        portfolio_row = cursor.fetchone()
        if portfolio_row:
            portfolio_id = portfolio_row['id']
            cursor.execute("""
                UPDATE portfolios
                SET cash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (portfolio['cash'], portfolio_id))
        else:
            cursor.execute("""
                INSERT INTO portfolios (user_id, cash)
                VALUES (?, ?)
            """, (user_id, portfolio['cash']))
            portfolio_id = cursor.lastrowid
        
        # Eski hisseleri sil
        cursor.execute("""
            DELETE FROM portfolio_stocks WHERE portfolio_id = ?
        """, (portfolio_id,))
        
        # Yeni hisseleri ekle
        for symbol, info in portfolio.get('stocks', {}).items():
            cursor.execute("""
                INSERT INTO portfolio_stocks (portfolio_id, symbol, quantity, avg_cost)
                VALUES (?, ?, ?, ?)
            """, (portfolio_id, symbol, info['quantity'], info['avg_cost']))
        
        conn.commit()
        conn.close()
        logger.info(f"Portföy güncellendi: User {user_id}")
    
    # === MIGRATION İŞLEMLERİ ===
    
    def migrate_json_transactions(self, old_user_id: str, new_user_id: int, json_file_path: str) -> int:
        """Eski JSON transaction'ları veritabanına aktar (duplicate kontrolü ile)"""
        if not os.path.exists(json_file_path):
            logger.warning(f"JSON dosyası bulunamadı: {json_file_path}")
            return 0
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                transactions = json.load(f)
            
            migrated_count = 0
            skipped_count = 0
            
            for transaction in transactions:
                try:
                    # Transaction formatını kontrol et
                    if not all(key in transaction for key in ['type', 'symbol', 'quantity', 'price', 'total_value', 'date']):
                        logger.warning(f"Eksik alanlar: {transaction}")
                        continue
                    
                    # Duplicate kontrolü
                    transaction_data = {
                        'type': transaction['type'],
                        'symbol': transaction['symbol'],
                        'quantity': transaction['quantity'],
                        'price': transaction['price'],
                        'total_value': transaction['total_value'],
                        'date': transaction['date']
                    }
                    
                    if self.check_transaction_exists(new_user_id, transaction_data):
                        skipped_count += 1
                        continue
                    
                    # Transaction'ı ekle
                    self.add_transaction(new_user_id, transaction_data)
                    migrated_count += 1
                except Exception as e:
                    logger.error(f"Transaction migrate hatası: {str(e)}")
                    continue
            
            logger.info(f"{migrated_count} transaction migrate edildi, {skipped_count} duplicate atlandı (User: {new_user_id})")
            return migrated_count
        except Exception as e:
            logger.error(f"JSON migrate hatası: {str(e)}")
            return 0

