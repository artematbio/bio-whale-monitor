#!/usr/bin/env python3
"""
Railway Database Viewer для DAO Treasury Monitor
Интерактивный просмотр Railway PostgreSQL базы данных
"""

import os
import sys
import getpass
from database_viewer import *

def get_railway_database_url():
    """Получение DATABASE_URL для Railway"""
    print("🚂 Railway PostgreSQL Database Viewer")
    print("="*50)
    print()
    print("Для подключения к Railway базе данных нужен DATABASE_URL.")
    print("Получите его из Railway dashboard -> Variables -> DATABASE_URL")
    print()
    print("Формат: postgresql://username:password@host:port/dbname")
    print()
    
    database_url = getpass.getpass("Введите DATABASE_URL (ввод скрыт): ")
    
    if not database_url:
        print("❌ DATABASE_URL не может быть пустым")
        return None
    
    if not database_url.startswith(('postgresql://', 'postgres://')):
        print("❌ DATABASE_URL должен начинаться с postgresql:// или postgres://")
        return None
    
    return database_url

def test_railway_connection(database_url):
    """Тестирование подключения к Railway"""
    print("\n🔄 Тестирование подключения к Railway...")
    
    # Временно устанавливаем DATABASE_URL
    original_url = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = database_url
    
    try:
        # Пытаемся создать подключение
        from database.postgresql_database import PostgreSQLDatabase
        database = PostgreSQLDatabase(database_url)
        
        print("✅ Подключение к Railway успешно!")
        return database
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")
        return None
    finally:
        # Восстанавливаем оригинальную переменную
        if original_url:
            os.environ['DATABASE_URL'] = original_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

def main():
    """Основная функция"""
    print("🚀 DAO Treasury Monitor - Railway Database Viewer")
    print("="*60)
    
    # Проверяем что PostgreSQL модуль доступен
    try:
        import psycopg2
        print("✅ PostgreSQL модуль доступен")
    except ImportError:
        print("❌ PostgreSQL модуль не установлен")
        print("Установите его: pip3 install psycopg2-binary")
        return
    
    # Получаем DATABASE_URL
    database_url = get_railway_database_url()
    if not database_url:
        return
    
    # Тестируем подключение
    database = test_railway_connection(database_url)
    if not database:
        return
    
    # Временно устанавливаем DATABASE_URL для database_viewer
    os.environ['DATABASE_URL'] = database_url
    
    try:
        print("\n📊 Railway Database Content:")
        print("="*60)
        
        # Показываем информацию о подключении
        show_connection_info(database)
        
        # Показываем статистику
        show_database_stats(database)
        
        # Показываем информацию о таблицах
        show_tables_info(database)
        
        # Показываем последние транзакции
        show_recent_transactions(database, 5)
        
        # Показываем последние алерты
        show_recent_alerts(database, 5)
        
        # Показываем сводку по DAO
        show_dao_summary(database)
        
        # Показываем ценовые данные
        show_price_data(database, 3)
        
        print("\n" + "="*60)
        print("✅ Railway database viewer completed successfully!")
        print("="*60)
        
        # Показываем команды для постоянного использования
        print("\n💡 Для постоянного доступа:")
        print("1. Добавьте DATABASE_URL в .env файл")
        print("2. Используйте команды: dbrailwaystats, dbrailwaytx, etc.")
        print("3. Или используйте: python3 database_viewer.py --railway")
        
    except Exception as e:
        print(f"❌ Ошибка при работе с Railway базой данных: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    finally:
        # Очищаем DATABASE_URL
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

if __name__ == "__main__":
    main() 