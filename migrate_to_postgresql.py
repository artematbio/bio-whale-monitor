#!/usr/bin/env python3
"""
Миграция данных из SQLite в PostgreSQL
Переносит все данные из локальной базы в Railway PostgreSQL
"""

import os
import sqlite3
import logging
from datetime import datetime
from database.database import DAOTreasuryDatabase
from database.postgresql_database import PostgreSQLDatabase

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_data():
    """Мигрирует данные из SQLite в PostgreSQL"""
    
    # Подключение к локальной SQLite
    sqlite_db = DAOTreasuryDatabase()
    
    # Подключение к Railway PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL не установлена!")
        return False
    
    postgresql_db = PostgreSQLDatabase(database_url)
    
    try:
        # Миграция treasury_transactions
        logger.info("🚀 Начинаем миграцию treasury_transactions...")
        
        # Получаем все транзакции из SQLite
        conn = sqlite3.connect(sqlite_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM treasury_transactions")
        transactions = cursor.fetchall()
        
        logger.info(f"📊 Найдено {len(transactions)} транзакций в SQLite")
        
        # Получаем структуру таблицы
        cursor.execute("PRAGMA table_info(treasury_transactions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrated_count = 0
        skipped_count = 0
        
        # Переносим каждую транзакцию
        for transaction in transactions:
            tx_data = dict(zip(columns, transaction))
            
            # Проверяем, нет ли уже такой транзакции в PostgreSQL
            if postgresql_db.is_transaction_processed(tx_data['tx_hash']):
                logger.debug(f"⏭️ Пропускаем дубликат: {tx_data['tx_hash']}")
                skipped_count += 1
                continue
            
            # Переносим транзакцию
            success = postgresql_db.save_treasury_transaction(tx_data)
            if success:
                migrated_count += 1
                logger.debug(f"✅ Перенесена: {tx_data['tx_hash']}")
            else:
                logger.error(f"❌ Ошибка переноса: {tx_data['tx_hash']}")
        
        conn.close()
        
        logger.info(f"💰 Treasury Transactions: {migrated_count} перенесено, {skipped_count} пропущено")
        
        # Миграция alerts
        logger.info("🚨 Начинаем миграцию alerts...")
        
        conn = sqlite3.connect(sqlite_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM alerts")
        alerts = cursor.fetchall()
        
        logger.info(f"📊 Найдено {len(alerts)} алертов в SQLite")
        
        # Получаем структуру таблицы alerts
        cursor.execute("PRAGMA table_info(alerts)")
        alert_columns = [row[1] for row in cursor.fetchall()]
        
        alert_migrated = 0
        alert_skipped = 0
        
        # Переносим каждый алерт
        for alert in alerts:
            alert_data = dict(zip(alert_columns, alert))
            
            # Сохраняем алерт в PostgreSQL
            try:
                success = postgresql_db.save_alert(alert_data)
                if success:
                    alert_migrated += 1
                else:
                    alert_skipped += 1
            except Exception as e:
                logger.error(f"❌ Ошибка переноса алерта: {e}")
                alert_skipped += 1
        
        conn.close()
        
        logger.info(f"🚨 Alerts: {alert_migrated} перенесено, {alert_skipped} пропущено")
        
        # Миграция token_prices
        logger.info("💎 Начинаем миграцию token_prices...")
        
        conn = sqlite3.connect(sqlite_db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM token_prices")
        prices = cursor.fetchall()
        
        logger.info(f"📊 Найдено {len(prices)} записей цен в SQLite")
        
        # Получаем структуру таблицы token_prices
        cursor.execute("PRAGMA table_info(token_prices)")
        price_columns = [row[1] for row in cursor.fetchall()]
        
        price_migrated = 0
        price_skipped = 0
        
        # Переносим цены пакетами
        for price in prices:
            price_data = dict(zip(price_columns, price))
            
            try:
                success = postgresql_db.save_token_price(
                    price_data['token_symbol'],
                    float(price_data['price_usd']),
                    price_data['source']
                )
                if success:
                    price_migrated += 1
                else:
                    price_skipped += 1
            except Exception as e:
                logger.error(f"❌ Ошибка переноса цены: {e}")
                price_skipped += 1
        
        conn.close()
        
        logger.info(f"💎 Token Prices: {price_migrated} перенесено, {price_skipped} пропущено")
        
        # Итоговая статистика
        logger.info("🎉 Миграция завершена!")
        logger.info(f"📊 Итого перенесено:")
        logger.info(f"  💰 Транзакции: {migrated_count}")
        logger.info(f"  🚨 Алерты: {alert_migrated}")
        logger.info(f"  💎 Цены: {price_migrated}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        return False

def check_migration_status():
    """Проверяет статус миграции"""
    
    # SQLite статистика
    sqlite_db = DAOTreasuryDatabase()
    
    conn = sqlite3.connect(sqlite_db.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM treasury_transactions")
    sqlite_tx_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts")
    sqlite_alerts_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM token_prices")
    sqlite_prices_count = cursor.fetchone()[0]
    
    conn.close()
    
    # PostgreSQL статистика
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL не установлена!")
        return
    
    try:
        import psycopg2
        pg_conn = psycopg2.connect(database_url)
        pg_cursor = pg_conn.cursor()
        
        pg_cursor.execute("SELECT COUNT(*) FROM treasury_transactions")
        result = pg_cursor.fetchone()
        pg_tx_count = result[0] if result else 0
        
        pg_cursor.execute("SELECT COUNT(*) FROM alerts")
        result = pg_cursor.fetchone()
        pg_alerts_count = result[0] if result else 0
        
        pg_cursor.execute("SELECT COUNT(*) FROM token_prices")
        result = pg_cursor.fetchone()
        pg_prices_count = result[0] if result else 0
        
        pg_conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        pg_tx_count = pg_alerts_count = pg_prices_count = "N/A"
    
    # Отчет
    logger.info("📊 Статус миграции:")
    logger.info("="*50)
    logger.info(f"SQLite (локальная):")
    logger.info(f"  💰 Транзакции: {sqlite_tx_count}")
    logger.info(f"  🚨 Алерты: {sqlite_alerts_count}")
    logger.info(f"  💎 Цены: {sqlite_prices_count}")
    logger.info("")
    logger.info(f"PostgreSQL (Railway):")
    logger.info(f"  💰 Транзакции: {pg_tx_count}")
    logger.info(f"  🚨 Алерты: {pg_alerts_count}")
    logger.info(f"  💎 Цены: {pg_prices_count}")
    logger.info("="*50)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_migration_status()
    else:
        print("🚀 DAO Treasury Monitor - Data Migration")
        print("=====================================")
        print("Миграция данных из SQLite в PostgreSQL")
        print("")
        
        # Проверка статуса до миграции
        print("📊 Статус ДО миграции:")
        check_migration_status()
        print("")
        
        # Подтверждение
        response = input("🤔 Продолжить миграцию? (y/N): ")
        if response.lower() in ['y', 'yes', 'да']:
            success = migrate_data()
            
            if success:
                print("")
                print("📊 Статус ПОСЛЕ миграции:")
                check_migration_status()
            else:
                print("❌ Миграция завершилась с ошибками!")
        else:
            print("❌ Миграция отменена") 