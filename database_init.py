#!/usr/bin/env python3
"""
Database Initialization Script for Railway PostgreSQL
Инициализирует базу данных с начальными данными
"""

import os
import asyncio
import logging
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

def get_database():
    """Получение экземпляра базы данных"""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url and POSTGRESQL_AVAILABLE:
        print("Using PostgreSQL database (Railway)")
        return PostgreSQLDatabase(database_url)
    else:
        print("Using SQLite database (Local)")
        return DAOTreasuryDatabase()

def initialize_sample_data(database):
    """Добавляет тестовые данные в базу если она пустая"""
    
    stats = database.get_database_stats()
    print(f"Current database stats: {stats}")
    
    # Проверяем есть ли уже данные
    if stats.get('treasury_transactions', 0) > 0:
        print("Database already has data, skipping initialization")
        return
    
    print("Database is empty, adding sample data...")
    
    # Добавляем тестовые транзакции
    sample_transactions = [
        {
            'tx_hash': 'sample_tx_1_ethereum_vitadao',
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
            'metadata': {'test': True, 'initialization': True}
        },
        {
            'tx_hash': 'sample_tx_2_solana_curetopia',
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
            'metadata': {'test': True, 'initialization': True}
        }
    ]
    
    # Сохраняем транзакции
    for tx in sample_transactions:
        success = database.save_treasury_transaction(tx)
        if success:
            print(f"✅ Added sample transaction: {tx['dao_name']} - ${tx['amount_usd']}")
        else:
            print(f"❌ Failed to add transaction: {tx['dao_name']}")
    
    # Добавляем тестовые алерты
    sample_alerts = [
        {
            'alert_type': 'price_drop',
            'dao_name': 'VitaDAO',
            'severity': 'medium',
            'title': 'Price Drop Alert - VITA',
            'message': 'VITA price dropped 8.5% in 1h',
            'timestamp': datetime.now() - timedelta(minutes=30),
            'metadata': {'test': True, 'initialization': True}
        },
        {
            'alert_type': 'large_transaction',
            'dao_name': 'Curetopia',
            'severity': 'high',
            'title': 'Large Transaction Alert',
            'message': 'Large incoming transfer detected',
            'timestamp': datetime.now() - timedelta(minutes=15),
            'metadata': {'test': True, 'initialization': True}
        }
    ]
    
    # Сохраняем алерты
    for alert in sample_alerts:
        success = database.save_alert(alert)
        if success:
            print(f"✅ Added sample alert: {alert['dao_name']} - {alert['alert_type']}")
        else:
            print(f"❌ Failed to add alert: {alert['dao_name']}")
    
    # Показываем финальную статистику
    final_stats = database.get_database_stats()
    print(f"\n🎯 Database initialized successfully!")
    print(f"Final stats: {final_stats}")

def main():
    """Основная функция"""
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Initializing DAO Treasury Monitor Database")
    print(f"Environment: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
    
    try:
        # Инициализируем базу данных
        database = get_database()
        
        # Добавляем начальные данные
        initialize_sample_data(database)
        
        print("✅ Database initialization completed")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 