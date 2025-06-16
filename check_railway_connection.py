#!/usr/bin/env python3
"""
Railway Connection Checker для DAO Treasury Monitor
Проверяет связь между системой мониторинга и Railway PostgreSQL
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_environment_variables():
    """Проверка переменных окружения"""
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("="*50)
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID', 
        'HELIUS_API_KEY',
        'COINGECKO_API_KEY'
    ]
    
    optional_vars = [
        'DATABASE_URL',
        'ETHEREUM_RPC_URL',
        'BITQUERY_API_KEY',
        'RAILWAY_ENVIRONMENT'
    ]
    
    print("✅ Обязательные переменные:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var}: {'*' * 10}...{value[-4:] if len(value) > 4 else '****'}")
        else:
            print(f"  {var}: ❌ НЕ УСТАНОВЛЕНА")
    
    print("\n🔧 Опциональные переменные:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            if var == 'DATABASE_URL':
                print(f"  {var}: {'*' * 20}...{value[-10:] if len(value) > 10 else '****'}")
            else:
                print(f"  {var}: {'*' * 10}...{value[-4:] if len(value) > 4 else '****'}")
        else:
            print(f"  {var}: ❌ НЕ УСТАНОВЛЕНА")

def check_database_connection():
    """Проверка подключения к базе данных"""
    print("\n🗄️ ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
    print("="*50)
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL не установлена")
        print("   Система будет использовать локальную SQLite базу")
        return False
    
    print(f"✅ DATABASE_URL найдена: {database_url[:30]}...{database_url[-10:]}")
    
    # Проверяем PostgreSQL модуль
    try:
        import psycopg2
        print("✅ psycopg2 модуль доступен")
    except ImportError:
        print("❌ psycopg2 модуль НЕ УСТАНОВЛЕН")
        print("   Установите его: pip3 install psycopg2-binary")
        return False
    
    # Пытаемся подключиться
    try:
        from database.postgresql_database import PostgreSQLDatabase
        db = PostgreSQLDatabase(database_url)
        print("✅ Подключение к PostgreSQL успешно!")
        
        # Проверяем статистику
        stats = db.get_database_stats()
        print(f"📊 Статистика базы данных:")
        print(f"   💰 Treasury Transactions: {stats.get('treasury_transactions', 0)}")
        print(f"   🚨 Alerts: {stats.get('alerts', 0)}")
        print(f"   💎 Token Prices: {stats.get('token_prices', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False

def check_system_status():
    """Проверка статуса системы мониторинга"""
    print("\n🚀 СТАТУС СИСТЕМЫ МОНИТОРИНГА")
    print("="*50)
    
    # Проверяем основные модули
    modules_to_check = [
        ('database.database', 'DAOTreasuryDatabase'),
        ('database.postgresql_database', 'PostgreSQLDatabase'),
        ('monitors.price_tracker', 'PriceTracker'),
        ('monitors.solana_monitor', 'SolanaMonitor'),
        ('monitors.ethereum_monitor', 'EthereumMonitor'),
        ('notifications.telegram_bot', 'TelegramBot')
    ]
    
    for module_name, class_name in modules_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {class_name} доступен")
        except ImportError as e:
            print(f"❌ {class_name} НЕ ДОСТУПЕН: {e}")
        except AttributeError:
            print(f"❌ {class_name} не найден в модуле {module_name}")

def generate_railway_instructions():
    """Генерация инструкций для Railway"""
    print("\n📋 ИНСТРУКЦИИ ДЛЯ RAILWAY SETUP")
    print("="*50)
    
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        print("✅ У вас есть DATABASE_URL - хорошо!")
        print("\n🔧 Шаги для настройки Railway:")
        print("1. Откройте Railway dashboard")
        print("2. Перейдите в проект 'bio-lp'")
        print("3. Откройте раздел Variables")
        print("4. Убедитесь что DATABASE_URL установлена:")
        print(f"   DATABASE_URL={database_url[:30]}...{database_url[-10:]}")
        print("5. Перезапустите deployment")
    else:
        print("❌ DATABASE_URL не найдена локально")
        print("\n🔧 Что нужно сделать:")
        print("1. Скопируйте DATABASE_URL из Railway PostgreSQL")
        print("2. Добавьте её в проект bio-lp Variables:")
        print("   - Откройте Railway dashboard")
        print("   - Проект bio-lp -> Variables")
        print("   - Добавьте DATABASE_URL = ваша_ссылка_postgresql")
        print("3. Перезапустите deployment")
    
    print("\n🚂 Команды для проверки после настройки:")
    print("   railwaydb                    # Интерактивный просмотр")
    print("   dbrailwaystats              # Статистика Railway БД")
    print("   python3 check_railway_connection.py  # Повторная проверка")

def main():
    """Основная функция"""
    print("🚀 DAO Treasury Monitor - Railway Connection Checker")
    print("="*60)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Проверяем переменные окружения
    check_environment_variables()
    
    # Проверяем подключение к базе данных
    db_connected = check_database_connection()
    
    # Проверяем статус системы
    check_system_status()
    
    # Генерируем инструкции
    generate_railway_instructions()
    
    print("\n" + "="*60)
    if db_connected:
        print("✅ СИСТЕМА ГОТОВА К РАБОТЕ С RAILWAY POSTGRESQL!")
    else:
        print("⚠️  ТРЕБУЕТСЯ НАСТРОЙКА RAILWAY POSTGRESQL")
    print("="*60)

if __name__ == "__main__":
    main() 