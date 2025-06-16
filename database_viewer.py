#!/usr/bin/env python3
"""
Database Viewer для DAO Treasury Monitor
Показывает содержимое базы данных в удобном формате
"""

import os
import sqlite3
import argparse
from datetime import datetime, timedelta
from decimal import Decimal

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database.database import DAOTreasuryDatabase

# Для Railway PostgreSQL
try:
    from database.postgresql_database import PostgreSQLDatabase
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

def get_database(force_railway=False, force_local=False):
    """Получение экземпляра базы данных"""
    database_url = os.getenv('DATABASE_URL')
    
    if force_railway:
        if not database_url or not POSTGRESQL_AVAILABLE:
            print("❌ Railway PostgreSQL not available or DATABASE_URL not set")
            print(f"DATABASE_URL present: {bool(database_url)}")
            print(f"PostgreSQL module available: {POSTGRESQL_AVAILABLE}")
            return None
        print("📊 Using PostgreSQL database (Railway) - FORCED")
        return PostgreSQLDatabase(database_url)
    
    if force_local:
        print("📊 Using SQLite database (Local) - FORCED")
        return DAOTreasuryDatabase()
    
    # Автоматическое определение
    if database_url and POSTGRESQL_AVAILABLE:
        print("📊 Using PostgreSQL database (Railway) - AUTO DETECTED")
        return PostgreSQLDatabase(database_url)
    else:
        print("📊 Using SQLite database (Local) - AUTO DETECTED")
        return DAOTreasuryDatabase()

def get_db_connection(database):
    """Получение соединения с базой данных"""
    if hasattr(database, 'connection_pool'):
        # PostgreSQL
        return database.get_connection()
    else:
        # SQLite
        return sqlite3.connect(database.db_path)

def close_db_connection(database, conn):
    """Закрытие соединения с базой данных"""
    if hasattr(database, 'connection_pool'):
        # PostgreSQL
        database.put_connection(conn)
    else:
        # SQLite
        conn.close()

def execute_query(database, query, params=None, fetch_all=True):
    """Выполнение запроса с правильным управлением соединениями"""
    conn = None
    try:
        conn = get_db_connection(database)
        
        if hasattr(database, 'connection_pool'):
            # PostgreSQL
            cursor = conn.cursor()
            if params:
                cursor.execute(query.replace('?', '%s'), params)
            else:
                cursor.execute(query)
        else:
            # SQLite
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
        
        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()
            
        return result
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        import traceback
        print(f"Query: {query}")
        print(f"Params: {params}")
        print(f"Traceback: {traceback.format_exc()}")
        return None
    finally:
        if conn:
            close_db_connection(database, conn)

def show_database_stats(database):
    """Показывает общую статистику базы данных"""
    stats = database.get_database_stats()
    
    print("\n" + "="*60)
    print("📊 DATABASE STATISTICS")
    print("="*60)
    
    print(f"💰 Treasury Transactions: {stats.get('treasury_transactions', 0)}")
    print(f"🚨 Alerts Generated: {stats.get('alerts', 0)}")
    print(f"🏊 Pool Activities: {stats.get('pool_activities', 0)}")
    print(f"📈 Balance Snapshots: {stats.get('balance_snapshots', 0)}")
    print(f"💾 Database Size: {stats.get('database_size_mb', 0):.2f} MB")

def show_recent_transactions(database, limit=10):
    """Показывает последние транзакции"""
    print("\n" + "="*60)
    print(f"💰 RECENT TREASURY TRANSACTIONS (Last {limit})")
    print("="*60)
    
    query = """
    SELECT dao_name, blockchain, token_symbol, amount, amount_usd, 
           tx_type, timestamp, tx_hash, alert_triggered
    FROM treasury_transactions 
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    transactions = execute_query(database, query, (limit,))
    
    if not transactions:
        print("❌ No transactions found")
        return
    
    for i, tx in enumerate(transactions, 1):
        dao_name, blockchain, token_symbol, amount, amount_usd, tx_type, timestamp, tx_hash, alert_triggered = tx
        
        # Форматируем timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        
        alert_icon = "🚨" if alert_triggered else "✅"
        print(f"\n{i}. {alert_icon} {dao_name} ({blockchain.upper()})")
        print(f"   💎 {tx_type.title()}: {amount:,.2f} {token_symbol} (${amount_usd:,.2f})")
        print(f"   🕒 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   🔗 {tx_hash[:20]}...{tx_hash[-10:]}")

def show_recent_alerts(database, limit=10):
    """Показывает последние алерты"""
    print("\n" + "="*60)
    print(f"🚨 RECENT ALERTS (Last {limit})")
    print("="*60)
    
    query = """
    SELECT dao_name, alert_type, severity, title, message, timestamp
    FROM alerts 
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    alerts = execute_query(database, query, (limit,))
    
    if not alerts:
        print("❌ No alerts found")
        return
    
    severity_icons = {
        'low': '🟢',
        'medium': '🟡', 
        'high': '🔴'
    }
    
    for i, alert in enumerate(alerts, 1):
        dao_name, alert_type, severity, title, message, timestamp = alert
        
        # Форматируем timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        
        icon = severity_icons.get(severity, '⚪')
        print(f"\n{i}. {icon} {title}")
        print(f"   🏛️ {dao_name} | 📋 {alert_type} | ⚠️ {severity}")
        print(f"   💬 {message}")
        print(f"   🕒 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

def show_dao_summary(database):
    """Показывает сводку по DAO"""
    print("\n" + "="*60)
    print("🏛️ DAO ACTIVITY SUMMARY")
    print("="*60)
    
    query = """
    SELECT dao_name, blockchain, COUNT(*) as tx_count, 
           SUM(amount_usd) as total_usd, AVG(amount_usd) as avg_usd
    FROM treasury_transactions 
    GROUP BY dao_name, blockchain
    ORDER BY total_usd DESC
    """
    
    summaries = execute_query(database, query)
    
    if not summaries:
        print("❌ No DAO activity found")
        return
    
    print(f"{'DAO Name':<15} {'Chain':<10} {'Txs':<5} {'Total USD':<12} {'Avg USD':<10}")
    print("-" * 60)
    
    for summary in summaries:
        dao_name, blockchain, tx_count, total_usd, avg_usd = summary
        total_usd = total_usd or 0
        avg_usd = avg_usd or 0
        print(f"{dao_name:<15} {blockchain:<10} {tx_count:<5} ${total_usd:<11,.0f} ${avg_usd:<9,.0f}")

def show_price_data(database, limit=5):
    """Показывает последние данные о ценах"""
    print("\n" + "="*60)
    print(f"💰 RECENT PRICE DATA (Last {limit})")
    print("="*60)
    
    query = """
    SELECT token_symbol, token_address, blockchain, price_usd, timestamp
    FROM token_prices 
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    prices = execute_query(database, query, (limit,))
    
    if not prices:
        print("❌ No price data found")
        return
    
    for i, price in enumerate(prices, 1):
        token_symbol, token_address, blockchain, price_usd, timestamp = price
        
        # Форматируем timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        
        print(f"\n{i}. 💎 {token_symbol} ({blockchain.upper()})")
        print(f"   💰 ${float(price_usd):.6f}")
        print(f"   🕒 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   📍 {token_address[:10]}...{token_address[-8:]}")

def show_tables_info(database):
    """Показывает информацию о таблицах"""
    print("\n" + "="*60)
    print("📋 DATABASE TABLES INFO")
    print("="*60)
    
    if hasattr(database, 'connection_pool'):
        # PostgreSQL
        query = """
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = t.table_name) as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        tables = execute_query(database, query)
    else:
        # SQLite
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        table_names = execute_query(database, query)
        
        tables = []
        for (table_name,) in table_names:
            columns_query = f"PRAGMA table_info({table_name})"
            columns = execute_query(database, columns_query)
            tables.append((table_name, len(columns)))
    
    if not tables:
        print("❌ No tables found")
        return
    
    print(f"{'Table Name':<25} {'Columns':<10} {'Records':<10}")
    print("-" * 50)
    
    for table_name, column_count in tables:
        # Получаем количество записей
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        result = execute_query(database, count_query, fetch_all=False)
        record_count = result[0] if result else 0
        
        print(f"{table_name:<25} {column_count:<10} {record_count:<10}")

def show_connection_info(database):
    """Показывает информацию о подключении"""
    print("\n" + "="*60)
    print("🔗 CONNECTION INFO")
    print("="*60)
    
    if hasattr(database, 'connection_pool'):
        print("Database Type: PostgreSQL (Railway)")
        print(f"Database URL: {database.database_url[:50]}..." if len(database.database_url) > 50 else database.database_url)
        print(f"Connection Pool: {database.connection_pool.minconn}-{database.connection_pool.maxconn} connections")
    else:
        print("Database Type: SQLite (Local)")
        print(f"Database Path: {database.db_path}")
        print(f"File exists: {os.path.exists(database.db_path)}")
        if os.path.exists(database.db_path):
            file_size = os.path.getsize(database.db_path) / (1024 * 1024)
            print(f"File size: {file_size:.2f} MB")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='DAO Treasury Monitor - Database Viewer')
    parser.add_argument('--mode', choices=['all', 'stats', 'transactions', 'alerts', 'dao', 'prices', 'tables', 'connection'], 
                       default='all', help='What to show')
    parser.add_argument('--limit', type=int, default=10, help='Number of records to show')
    parser.add_argument('--railway', action='store_true', help='Force use Railway PostgreSQL database')
    parser.add_argument('--local', action='store_true', help='Force use local SQLite database')
    
    args = parser.parse_args()
    
    print("🚀 DAO Treasury Monitor - Database Viewer")
    print(f"Environment: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
    
    if args.railway and args.local:
        print("❌ Cannot use both --railway and --local flags")
        return
    
    try:
        database = get_database(force_railway=args.railway, force_local=args.local)
        if not database:
            return
        
        if args.mode in ['all', 'connection']:
            show_connection_info(database)
        
        if args.mode in ['all', 'stats']:
            show_database_stats(database)
        
        if args.mode in ['all', 'tables']:
            show_tables_info(database)
        
        if args.mode in ['all', 'transactions']:
            show_recent_transactions(database, args.limit)
        
        if args.mode in ['all', 'alerts']:
            show_recent_alerts(database, args.limit)
        
        if args.mode in ['all', 'dao']:
            show_dao_summary(database)
        
        if args.mode in ['all', 'prices']:
            show_price_data(database, args.limit)
        
        print("\n" + "="*60)
        print("✅ Database viewer completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Database viewer failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 