#!/usr/bin/env python3
"""
PostgreSQL Database для DAO Treasury Monitor
Адаптер для Railway deployment с PostgreSQL
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger(__name__)

class PostgreSQLDatabase:
    """Класс для работы с PostgreSQL базой данных на Railway"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required for PostgreSQL")
        
        # Создаем connection pool
        self.connection_pool = None
        self.init_connection_pool()
        self.init_database()
    
    def init_connection_pool(self):
        """Инициализация connection pool"""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20,  # min and max connections
                self.database_url,
                cursor_factory=RealDictCursor
            )
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Получение соединения из пула"""
        return self.connection_pool.getconn()
    
    def put_connection(self, conn):
        """Возврат соединения в пул"""
        self.connection_pool.putconn(conn)
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Таблица для транзакций treasury
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS treasury_transactions (
                    id SERIAL PRIMARY KEY,
                    tx_hash VARCHAR(255) UNIQUE NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    dao_name VARCHAR(100) NOT NULL,
                    blockchain VARCHAR(50) NOT NULL,
                    from_address VARCHAR(255) NOT NULL,
                    to_address VARCHAR(255) NOT NULL,
                    token_address VARCHAR(255) NOT NULL,
                    token_symbol VARCHAR(20) NOT NULL,
                    amount DECIMAL NOT NULL,
                    amount_usd DECIMAL NOT NULL,
                    tx_type VARCHAR(20) NOT NULL,
                    alert_triggered BOOLEAN DEFAULT FALSE,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для pool активности
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pool_activities (
                    id SERIAL PRIMARY KEY,
                    tx_hash VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    dao_name VARCHAR(100) NOT NULL,
                    blockchain VARCHAR(50) NOT NULL,
                    pool_address VARCHAR(255) NOT NULL,
                    activity_type VARCHAR(50) NOT NULL,
                    token0_address VARCHAR(255),
                    token1_address VARCHAR(255),
                    token0_symbol VARCHAR(20),
                    token1_symbol VARCHAR(20),
                    token0_amount DECIMAL,
                    token1_amount DECIMAL,
                    total_usd_value DECIMAL,
                    alert_triggered BOOLEAN DEFAULT FALSE,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для balance snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balance_snapshots (
                    id SERIAL PRIMARY KEY,
                    dao_name VARCHAR(100) NOT NULL,
                    blockchain VARCHAR(50) NOT NULL,
                    treasury_address VARCHAR(255) NOT NULL,
                    token_address VARCHAR(255) NOT NULL,
                    token_symbol VARCHAR(20) NOT NULL,
                    balance DECIMAL NOT NULL,
                    balance_usd DECIMAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для алертов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    alert_type VARCHAR(50) NOT NULL,
                    dao_name VARCHAR(100) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    tx_hash VARCHAR(255),
                    amount_usd DECIMAL,
                    sent_telegram BOOLEAN DEFAULT FALSE,
                    sent_discord BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для отслеживания исторических цен токенов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_prices (
                    id SERIAL PRIMARY KEY,
                    token_address VARCHAR(255) NOT NULL,
                    token_symbol VARCHAR(20) NOT NULL,
                    blockchain VARCHAR(50) NOT NULL,
                    price_usd DECIMAL(20, 10) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    market_cap_usd DECIMAL(20, 2),
                    volume_24h_usd DECIMAL(20, 2),
                    price_change_24h DECIMAL(10, 4),
                    metadata JSONB
                )
            """)
            
            # Создаем индексы
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_treasury_tx_dao_timestamp 
                ON treasury_transactions(dao_name, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_treasury_tx_hash 
                ON treasury_transactions(tx_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pool_activities_dao_timestamp 
                ON pool_activities(dao_name, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_prices_address_timestamp 
                ON token_prices(token_address, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_prices_symbol_timestamp 
                ON token_prices(token_symbol, timestamp)
            """)
            
            conn.commit()
            logger.info("PostgreSQL database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL database: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.put_connection(conn)
    
    def save_treasury_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Сохранение транзакции treasury"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO treasury_transactions 
                (tx_hash, timestamp, dao_name, blockchain, from_address, to_address, 
                 token_address, token_symbol, amount, amount_usd, tx_type, 
                 alert_triggered, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash) DO UPDATE SET
                amount_usd = EXCLUDED.amount_usd,
                alert_triggered = EXCLUDED.alert_triggered
            """, (
                tx_data['tx_hash'],
                tx_data['timestamp'],
                tx_data['dao_name'],
                tx_data['blockchain'],
                tx_data['from_address'],
                tx_data['to_address'],
                tx_data['token_address'],
                tx_data['token_symbol'],
                float(tx_data['amount']),
                float(tx_data['amount_usd']),
                tx_data['tx_type'],
                tx_data.get('alert_triggered', False),
                json.dumps(tx_data.get('metadata', {}))
            ))
            
            conn.commit()
            logger.info(f"Saved treasury transaction: {tx_data['tx_hash']} - {tx_data['dao_name']} - ${tx_data['amount_usd']:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving treasury transaction: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.put_connection(conn)
    
    def save_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Сохранение алерта"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO alerts 
                (alert_type, dao_name, severity, title, message, tx_hash, 
                 amount_usd, sent_telegram, sent_discord, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert_data['alert_type'],
                alert_data['dao_name'],
                alert_data['severity'],
                alert_data['title'],
                alert_data['message'],
                alert_data.get('tx_hash'),
                alert_data.get('amount_usd'),
                alert_data.get('sent_telegram', False),
                alert_data.get('sent_discord', False),
                alert_data['timestamp']
            ))
            
            conn.commit()
            logger.info(f"Saved alert: {alert_data['alert_type']} - {alert_data['dao_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.put_connection(conn)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Получение статистики базы данных"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Количество записей в таблицах
            cursor.execute("SELECT COUNT(*) FROM treasury_transactions")
            stats['treasury_transactions'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pool_activities")
            stats['pool_activities'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM balance_snapshots")
            stats['balance_snapshots'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts")
            stats['alerts'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM token_prices")
            stats['token_prices'] = cursor.fetchone()[0]
            
            # Размер базы данных
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                       pg_database_size(current_database()) / (1024*1024) as size_mb
            """)
            size_info = cursor.fetchone()
            stats['database_size'] = size_info[0]
            stats['database_size_mb'] = float(size_info[1])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
        finally:
            if conn:
                self.put_connection(conn)
    
    def get_recent_alerts(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение недавних алертов"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT alert_type, dao_name, severity, title, message, 
                       tx_hash, amount_usd, sent_telegram, sent_discord, 
                       timestamp, created_at
                FROM alerts 
                WHERE timestamp >= %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (since_time, limit))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'alert_type': row[0],
                    'dao_name': row[1],
                    'severity': row[2],
                    'title': row[3],
                    'message': row[4],
                    'tx_hash': row[5],
                    'amount_usd': float(row[6]) if row[6] else None,
                    'sent_telegram': row[7],
                    'sent_discord': row[8],
                    'timestamp': row[9].isoformat(),
                    'created_at': row[10].isoformat()
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
        finally:
            if conn:
                self.put_connection(conn)
    
    def is_transaction_processed(self, tx_hash: str) -> bool:
        """Проверка, была ли транзакция уже обработана"""
        try:
            # Используем прямое подключение вместо connection pool
            import psycopg2
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM treasury_transactions WHERE tx_hash = %s
            """, (tx_hash,))
            
            result = cursor.fetchone()
            count = result[0] if result else 0
            conn.close()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking transaction {tx_hash}: {e}")
            return False
    
    def is_alert_sent_for_transaction(self, tx_hash: str) -> bool:
        """Проверка, был ли уже отправлен алерт для данной транзакции"""
        try:
            # Используем прямое подключение вместо connection pool
            import psycopg2
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE tx_hash = %s AND alert_type = 'large_transaction'
            """, (tx_hash,))
            
            result = cursor.fetchone()
            count = result[0] if result else 0
            conn.close()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking alert for transaction {tx_hash}: {e}")
            return False
    
    def save_token_price(self, price_data: Dict[str, Any]) -> bool:
        """Сохранение цены токена"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO token_prices (
                    token_address, token_symbol, blockchain, price_usd,
                    timestamp, market_cap_usd, volume_24h_usd, 
                    price_change_24h, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                price_data['token_address'],
                price_data['token_symbol'], 
                price_data['blockchain'],
                float(price_data['price_usd']),
                price_data.get('timestamp', datetime.now()),
                price_data.get('market_cap_usd'),
                price_data.get('volume_24h_usd'),
                price_data.get('price_change_24h'),
                json.dumps(price_data.get('metadata', {}))
            ))
            
            conn.commit()
            logger.debug(f"Saved token price: {price_data['token_symbol']} - ${price_data['price_usd']:.6f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving token price: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.put_connection(conn)
    
    def get_latest_token_price(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Получение последней цены токена"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT token_address, token_symbol, blockchain, price_usd,
                       timestamp, market_cap_usd, volume_24h_usd, 
                       price_change_24h, metadata
                FROM token_prices 
                WHERE token_address = %s
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (token_address,))
            
            row = cursor.fetchone()
            if row:
                price_data = {
                    'token_address': row[0],
                    'token_symbol': row[1],
                    'blockchain': row[2],
                    'price_usd': float(row[3]),
                    'timestamp': row[4],
                    'market_cap_usd': row[5],
                    'volume_24h_usd': row[6],
                    'price_change_24h': row[7],
                    'metadata': json.loads(row[8]) if row[8] else {}
                }
                return price_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest token price: {e}")
            return None
        finally:
            if conn:
                self.put_connection(conn)
    
    def get_token_price_history(self, token_address: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Получение истории цен токена за период"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT token_address, token_symbol, blockchain, price_usd,
                       timestamp, market_cap_usd, volume_24h_usd, 
                       price_change_24h, metadata
                FROM token_prices 
                WHERE token_address = %s 
                AND timestamp >= %s
                ORDER BY timestamp DESC
            """, (token_address, since_time))
            
            prices = []
            for row in cursor.fetchall():
                price_data = {
                    'token_address': row[0],
                    'token_symbol': row[1],
                    'blockchain': row[2],
                    'price_usd': float(row[3]),
                    'timestamp': row[4],
                    'market_cap_usd': row[5],
                    'volume_24h_usd': row[6],
                    'price_change_24h': row[7],
                    'metadata': json.loads(row[8]) if row[8] else {}
                }
                prices.append(price_data)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting token price history: {e}")
            return []
        finally:
            if conn:
                self.put_connection(conn)
    
    def get_price_change_percentage(self, token_address: str, hours: int = 1) -> Optional[float]:
        """Вычисление процентного изменения цены за период"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем последнюю цену
            cursor.execute("""
                SELECT price_usd FROM token_prices 
                WHERE token_address = %s
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (token_address,))
            
            current_row = cursor.fetchone()
            if not current_row:
                return None
            
            current_price = float(current_row[0])
            
            # Получаем цену N часов назад
            past_time = datetime.now() - timedelta(hours=hours)
            cursor.execute("""
                SELECT price_usd FROM token_prices 
                WHERE token_address = %s 
                AND timestamp <= %s
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (token_address, past_time))
            
            past_row = cursor.fetchone()
            if not past_row:
                return None
            
            past_price = float(past_row[0])
            
            if past_price == 0:
                return None
            
            # Вычисляем процентное изменение
            change_percentage = ((current_price - past_price) / past_price) * 100
            return round(change_percentage, 2)
            
        except Exception as e:
            logger.error(f"Error calculating price change: {e}")
            return None
        finally:
            if conn:
                self.put_connection(conn)
    
    def cleanup_old_prices(self, days: int = 30) -> int:
        """Удаление старых записей цен (старше N дней)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(days=days)
            cursor.execute("""
                DELETE FROM token_prices 
                WHERE timestamp < %s
            """, (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old price records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old prices: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                self.put_connection(conn)
    
    def close(self):
        """Закрытие connection pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed") 