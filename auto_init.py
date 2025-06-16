#!/usr/bin/env python3
"""
Auto Database Initialization for Railway and Local
Автоматически инициализирует базу данных с проверкой окружения
"""

import os
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def detect_environment():
    """Определяет окружение (Railway, Local)"""
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return 'Railway'
    elif os.getenv('DATABASE_URL'):
        return 'PostgreSQL'
    else:
        return 'Local'

def get_database():
    """Получение экземпляра базы данных с автоопределением"""
    env = detect_environment()
    print(f"🌍 Detected environment: {env}")
    
    try:
        if env in ['Railway', 'PostgreSQL']:
            from database.postgresql_database import PostgreSQLDatabase
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                print(f"✅ Using PostgreSQL database")
                print(f"   Host: {database_url.split('@')[1].split(':')[0] if '@' in database_url else 'Unknown'}")
                return PostgreSQLDatabase(database_url)
            else:
                print("❌ DATABASE_URL not found, falling back to SQLite")
                raise ImportError("No DATABASE_URL")
        else:
            raise ImportError("Using SQLite")
            
    except ImportError:
        from database.database import DAOTreasuryDatabase
        print("✅ Using SQLite database (Local)")
        return DAOTreasuryDatabase()

def check_database_status(database):
    """Проверяет статус базы данных"""
    try:
        stats = database.get_database_stats()
        print(f"\n📊 Database Status:")
        print(f"   Treasury transactions: {stats.get('treasury_transactions', 0)}")
        print(f"   Alerts: {stats.get('alerts', 0)}")
        print(f"   Pool activities: {stats.get('pool_activities', 0)}")
        print(f"   Database size: {stats.get('database_size_mb', 0):.2f} MB")
        
        if stats.get('treasury_transactions', 0) == 0:
            print("\n🚨 Database appears to be empty!")
            return True  # Needs initialization
        else:
            print("\n✅ Database has data")
            return False  # Already initialized
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return True  # Try to initialize

def add_sample_data(database):
    """Добавляет образцы данных"""
    print("\n🔧 Adding sample data...")
    
    # Образцы транзакций
    sample_transactions = [
        {
            'tx_hash': f'init_tx_1_{int(datetime.now().timestamp())}',
            'timestamp': datetime.now() - timedelta(hours=2),
            'dao_name': 'VitaDAO',
            'blockchain': 'ethereum',
            'from_address': '0x03043470a266cf0cc85ca2050f4a66c3f4bfd097',
            'to_address': '0x1234567890123456789012345678901234567890',
            'token_address': '0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321',
            'token_symbol': 'VITA',
            'amount': Decimal('5000.0'),
            'amount_usd': Decimal('12500.0'),
            'tx_type': 'outgoing',
            'alert_triggered': True,
            'metadata': {'auto_init': True, 'environment': detect_environment()}
        },
        {
            'tx_hash': f'init_tx_2_{int(datetime.now().timestamp())}',
            'timestamp': datetime.now() - timedelta(hours=1),
            'dao_name': 'Curetopia',
            'blockchain': 'solana',
            'from_address': 'GnJ7vjun5sgt8is79LHAwFf6vPk47hncFPWNfeuYMjVP',
            'to_address': '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',
            'token_address': '9qU3LmwKJKT2DJeGPihyTP2jc6pC7ij3hPFeyJVzuksN',
            'token_symbol': 'CURES',
            'amount': Decimal('750000.0'),
            'amount_usd': Decimal('16700.0'),
            'tx_type': 'incoming',
            'alert_triggered': True,
            'metadata': {'auto_init': True, 'environment': detect_environment()}
        }
    ]
    
    # Сохраняем транзакции
    success_count = 0
    for tx in sample_transactions:
        if database.save_treasury_transaction(tx):
            print(f"   ✅ Added: {tx['dao_name']} ${tx['amount_usd']}")
            success_count += 1
        else:
            print(f"   ❌ Failed: {tx['dao_name']}")
    
    # Образцы алертов
    sample_alerts = [
        {
            'alert_type': 'price_drop',
            'dao_name': 'VitaDAO',
            'severity': 'medium',
            'title': 'Price Drop Alert - VITA',
            'message': 'VITA price dropped 8.5% in 1h',
            'timestamp': datetime.now() - timedelta(minutes=30),
            'metadata': {'auto_init': True, 'environment': detect_environment()}
        },
        {
            'alert_type': 'large_transaction',
            'dao_name': 'Curetopia',
            'severity': 'high',
            'title': 'Large Transaction Alert',
            'message': 'Large incoming transfer detected',
            'timestamp': datetime.now() - timedelta(minutes=15),
            'metadata': {'auto_init': True, 'environment': detect_environment()}
        }
    ]
    
    # Сохраняем алерты
    for alert in sample_alerts:
        if database.save_alert(alert):
            print(f"   ✅ Added alert: {alert['dao_name']} - {alert['alert_type']}")
            success_count += 1
        else:
            print(f"   ❌ Failed alert: {alert['dao_name']}")
    
    print(f"\n🎯 Added {success_count} records successfully")
    return success_count > 0

def main():
    """Основная функция автоинициализации"""
    print("🚀 DAO Treasury Monitor - Auto Database Initialization")
    print("=" * 60)
    
    # Показываем переменные окружения (без паролей)
    print("\n🔍 Environment Variables:")
    print(f"   RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")
    print(f"   DATABASE_URL: {'Set' if os.getenv('DATABASE_URL') else 'Not set'}")
    print(f"   HELIUS_API_KEY: {'Set' if os.getenv('HELIUS_API_KEY') else 'Not set'}")
    print(f"   TELEGRAM_BOT_TOKEN: {'Set' if os.getenv('TELEGRAM_BOT_TOKEN') else 'Not set'}")
    
    try:
        # Получаем базу данных
        database = get_database()
        
        # Проверяем статус
        needs_init = check_database_status(database)
        
        if needs_init:
            print("\n🔧 Database needs initialization...")
            success = add_sample_data(database)
            if success:
                print("\n✅ Database initialized successfully!")
                # Проверяем финальный статус
                check_database_status(database)
            else:
                print("\n❌ Database initialization failed!")
        else:
            print("\n✅ Database is already initialized, no action needed")
        
    except Exception as e:
        print(f"\n❌ Auto-initialization failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        print(f"\n💡 Manual steps:")
        print(f"1. Check DATABASE_URL in Railway dashboard")
        print(f"2. Verify PostgreSQL service is running")
        print(f"3. Check network connectivity")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Уменьшаем логирование
    main() 