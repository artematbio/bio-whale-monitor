#!/usr/bin/env python3
"""
База данных для DAO Treasury Monitor
SQLite база для логирования транзакций и pool активности
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

class DAOTreasuryDatabase:
    """Класс для работы с базой данных мониторинга DAO"""
    
    def __init__(self, db_path: str = "dao_treasury_monitor.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица для транзакций treasury
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS treasury_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_hash TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    dao_name TEXT NOT NULL,
                    blockchain TEXT NOT NULL,
                    from_address TEXT NOT NULL,
                    to_address TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    token_symbol TEXT NOT NULL,
                    amount DECIMAL NOT NULL,
                    amount_usd DECIMAL NOT NULL,
                    tx_type TEXT NOT NULL,
                    alert_triggered BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для pool активности
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pool_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_hash TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    dao_name TEXT NOT NULL,
                    blockchain TEXT NOT NULL,
                    pool_address TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    token0_address TEXT,
                    token1_address TEXT,
                    token0_symbol TEXT,
                    token1_symbol TEXT,
                    token0_amount DECIMAL,
                    token1_amount DECIMAL,
                    total_usd_value DECIMAL,
                    alert_triggered BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для balance snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dao_name TEXT NOT NULL,
                    blockchain TEXT NOT NULL,
                    treasury_address TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    token_symbol TEXT NOT NULL,
                    balance DECIMAL NOT NULL,
                    balance_usd DECIMAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для алертов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    dao_name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    tx_hash TEXT,
                    amount_usd DECIMAL,
                    sent_telegram BOOLEAN DEFAULT FALSE,
                    sent_discord BOOLEAN DEFAULT FALSE,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индексы для оптимизации
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_treasury_tx_dao_timestamp 
                ON treasury_transactions(dao_name, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_treasury_tx_hash 
                ON treasury_transactions(tx_hash)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_pool_activities_dao_timestamp 
                ON pool_activities(dao_name, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp)
            ''')
            
            # Таблица для отслеживания исторических цен токенов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT NOT NULL,
                    token_symbol TEXT NOT NULL,
                    blockchain TEXT NOT NULL,
                    price_usd DECIMAL(20, 10) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    market_cap_usd DECIMAL(20, 2),
                    volume_24h_usd DECIMAL(20, 2),
                    price_change_24h DECIMAL(10, 4),
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_prices_address_timestamp 
                ON token_prices(token_address, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_prices_symbol_timestamp 
                ON token_prices(token_symbol, timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized successfully: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_treasury_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Сохранение транзакции treasury"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO treasury_transactions 
                (tx_hash, timestamp, dao_name, blockchain, from_address, to_address, 
                 token_address, token_symbol, amount, amount_usd, tx_type, 
                 alert_triggered, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.close()
            
            logger.info(f"Saved treasury transaction: {tx_data['tx_hash']} - {tx_data['dao_name']} - ${tx_data['amount_usd']:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving treasury transaction: {e}")
            return False
    
    def save_pool_activity(self, activity_data: Dict[str, Any]) -> bool:
        """Сохранение активности в пуле"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO pool_activities 
                (tx_hash, timestamp, dao_name, blockchain, pool_address, activity_type,
                 token0_address, token1_address, token0_symbol, token1_symbol,
                 token0_amount, token1_amount, total_usd_value, alert_triggered, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_data['tx_hash'],
                activity_data['timestamp'],
                activity_data['dao_name'],
                activity_data['blockchain'],
                activity_data['pool_address'],
                activity_data['activity_type'],
                activity_data.get('token0_address'),
                activity_data.get('token1_address'),
                activity_data.get('token0_symbol'),
                activity_data.get('token1_symbol'),
                float(activity_data.get('token0_amount', 0)),
                float(activity_data.get('token1_amount', 0)),
                float(activity_data['total_usd_value']),
                activity_data.get('alert_triggered', False),
                json.dumps(activity_data.get('metadata', {}))
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved pool activity: {activity_data['tx_hash']} - {activity_data['dao_name']} - ${activity_data['total_usd_value']:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving pool activity: {e}")
            return False
    
    def save_balance_snapshot(self, balance_data: Dict[str, Any]) -> bool:
        """Сохранение снимка баланса treasury"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO balance_snapshots 
                (dao_name, blockchain, treasury_address, token_address, token_symbol,
                 balance, balance_usd, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                balance_data['dao_name'],
                balance_data['blockchain'],
                balance_data['treasury_address'],
                balance_data['token_address'],
                balance_data['token_symbol'],
                float(balance_data['balance']),
                float(balance_data['balance_usd']),
                balance_data['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Saved balance snapshot: {balance_data['dao_name']} - {balance_data['token_symbol']} - ${balance_data['balance_usd']:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving balance snapshot: {e}")
            return False
    
    def save_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Сохранение алерта"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO alerts 
                (alert_type, dao_name, severity, title, message, tx_hash, 
                 amount_usd, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_data['alert_type'],
                alert_data['dao_name'],
                alert_data['severity'],
                alert_data['title'],
                alert_data['message'],
                alert_data.get('tx_hash'),
                float(alert_data.get('amount_usd', 0)),
                alert_data['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved alert: {alert_data['alert_type']} - {alert_data['dao_name']} - {alert_data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            return False
    
    def get_recent_transactions(self, dao_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Получение недавних транзакций"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            if dao_name:
                cursor.execute("""
                    SELECT * FROM treasury_transactions 
                    WHERE dao_name = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (dao_name, since_time))
            else:
                cursor.execute("""
                    SELECT * FROM treasury_transactions 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (since_time,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return []
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Получение дневной сводки активности"""
        try:
            if date is None:
                date = datetime.now().date()
            
            start_time = datetime.combine(date, datetime.min.time())
            end_time = datetime.combine(date, datetime.max.time())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Статистика по treasury транзакциям
            cursor.execute("""
                SELECT 
                    dao_name,
                    COUNT(*) as tx_count,
                    SUM(amount_usd) as total_volume,
                    AVG(amount_usd) as avg_amount
                FROM treasury_transactions 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY dao_name
            """, (start_time, end_time))
            
            treasury_stats = cursor.fetchall()
            
            # Статистика по pool активности
            cursor.execute("""
                SELECT 
                    dao_name,
                    activity_type,
                    COUNT(*) as activity_count,
                    SUM(total_usd_value) as total_volume
                FROM pool_activities 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY dao_name, activity_type
            """, (start_time, end_time))
            
            pool_stats = cursor.fetchall()
            
            # Алерты за день
            cursor.execute("""
                SELECT 
                    alert_type,
                    COUNT(*) as alert_count
                FROM alerts 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY alert_type
            """, (start_time, end_time))
            
            alert_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                'date': date.isoformat(),
                'treasury_stats': treasury_stats,
                'pool_stats': pool_stats,
                'alert_stats': alert_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {}
    
    def is_transaction_processed(self, tx_hash: str) -> bool:
        """Проверка, была ли транзакция уже обработана"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM treasury_transactions WHERE tx_hash = ?
            """, (tx_hash,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking transaction: {e}")
            return False
    
    def is_alert_sent_for_transaction(self, tx_hash: str) -> bool:
        """Проверка, был ли уже отправлен алерт для данной транзакции"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE tx_hash = ? AND alert_type = 'large_transaction'
            """, (tx_hash,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking alert for transaction: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Получение статистики базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Подсчет записей в таблицах
            cursor.execute("SELECT COUNT(*) FROM treasury_transactions")
            treasury_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pool_activities") 
            pool_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM balance_snapshots")
            balance_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts")
            alert_count = cursor.fetchone()[0]
            
            # Размер файла базы данных
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            conn.close()
            
            return {
                'treasury_transactions': treasury_count,
                'pool_activities': pool_count,
                'balance_snapshots': balance_count,
                'alerts': alert_count,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def get_recent_alerts(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение последних алертов"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM alerts 
                WHERE timestamp >= datetime('now', '-{} hours')
                ORDER BY timestamp DESC 
                LIMIT ?
            """.format(hours), (limit,))
            
            alerts = []
            for row in cursor.fetchall():
                alert = dict(row)
                # Парсим JSON поля если они существуют
                if 'metadata' in alert and alert['metadata']:
                    try:
                        alert['metadata'] = json.loads(alert['metadata'])
                    except:
                        alert['metadata'] = {}
                else:
                    alert['metadata'] = {}
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
        finally:
            if conn:
                conn.close()

    # === МЕТОДЫ ДЛЯ ТРЕКИНГА ЦЕН ТОКЕНОВ ===
    
    def save_token_price(self, price_data: Dict[str, Any]) -> bool:
        """Сохранение цены токена"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO token_prices (
                    token_address, token_symbol, blockchain, price_usd,
                    timestamp, market_cap_usd, volume_24h_usd, 
                    price_change_24h, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            return True
            
        except Exception as e:
            logger.error(f"Error saving token price: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_latest_token_price(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Получение последней цены токена"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM token_prices 
                WHERE token_address = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (token_address,))
            
            row = cursor.fetchone()
            if row:
                price_data = dict(row)
                if price_data['metadata']:
                    try:
                        price_data['metadata'] = json.loads(price_data['metadata'])
                    except:
                        price_data['metadata'] = {}
                return price_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest token price: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_token_price_history(self, token_address: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Получение истории цен токена за период"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM token_prices 
                WHERE token_address = ? 
                AND timestamp >= datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours), (token_address,))
            
            prices = []
            for row in cursor.fetchall():
                price_data = dict(row)
                if price_data['metadata']:
                    try:
                        price_data['metadata'] = json.loads(price_data['metadata'])
                    except:
                        price_data['metadata'] = {}
                prices.append(price_data)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting token price history: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_price_change_percentage(self, token_address: str, hours: int = 1) -> Optional[float]:
        """Вычисление процентного изменения цены за период"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем последнюю цену
            cursor.execute("""
                SELECT price_usd FROM token_prices 
                WHERE token_address = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (token_address,))
            
            current_row = cursor.fetchone()
            if not current_row:
                return None
            
            current_price = float(current_row[0])
            
            # Получаем цену N часов назад
            cursor.execute("""
                SELECT price_usd FROM token_prices 
                WHERE token_address = ? 
                AND timestamp <= datetime('now', '-{} hours')
                ORDER BY timestamp DESC 
                LIMIT 1
            """.format(hours), (token_address,))
            
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
                conn.close()
    
    def cleanup_old_prices(self, days: int = 30):
        """Удаление старых записей цен (старше N дней)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM token_prices 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old price records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old prices: {e}")
            return 0
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    # Тестирование базы данных
    logging.basicConfig(level=logging.INFO)
    
    db = DAOTreasuryDatabase("test_dao_monitor.db")
    
    # Тестовые данные
    test_tx = {
        'tx_hash': 'test_hash_123',
        'timestamp': datetime.now(),
        'dao_name': 'VitaDAO',
        'blockchain': 'ethereum',
        'from_address': '0xF5307a74d1550739ef81c6488DC5C7a6a53e5Ac2',
        'to_address': '0x1234567890abcdef1234567890abcdef12345678',
        'token_address': '0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321',
        'token_symbol': 'VITA',
        'amount': Decimal('1000'),
        'amount_usd': Decimal('15000'),
        'tx_type': 'transfer',
        'alert_triggered': True,
        'metadata': {'test': 'data'}
    }
    
    # Тест сохранения
    success = db.save_treasury_transaction(test_tx)
    print(f"Transaction saved: {success}")
    
    # Тест получения статистики
    stats = db.get_database_stats()
    print(f"Database stats: {stats}")
    
    # Очистка тестовой базы
    import os
    if os.path.exists("test_dao_monitor.db"):
        os.remove("test_dao_monitor.db")
        print("Test database cleaned up") 