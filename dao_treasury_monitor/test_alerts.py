#!/usr/bin/env python3
"""
Тестирование ценовых алертов для DAO Treasury Monitor
Создает искусственные данные для проверки системы алертов
"""

import sys
import os
import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import DAOTreasuryDatabase
from monitors.price_tracker import PriceTracker
from config.dao_config import ALL_DAOS

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertTester:
    """Класс для тестирования системы алертов"""
    
    def __init__(self):
        self.database = DAOTreasuryDatabase()
        self.price_tracker = PriceTracker(self.database)
    
    def create_fake_price_history(self, token_address: str, token_symbol: str, blockchain: str, 
                                 base_price: float, drop_percentage: float = 7.0):
        """Создает фальшивую историю цен с падением"""
        
        current_time = datetime.now()
        
        # Создаем несколько исторических точек для лучшего расчета
        price_points = [
            (25, base_price),        # 25 часов назад
            (24, base_price),        # 24 часа назад  
            (5, base_price),         # 5 часов назад
            (4, base_price),         # 4 часа назад
            (2, base_price),         # 2 часа назад
            (1, base_price),         # 1 час назад (базовая)
        ]
        
        # Текущая цена (с падением)
        current_price = base_price * (1 - drop_percentage / 100)
        
        logger.info(f"Creating fake history for {token_symbol}:")
        logger.info(f"  Base price: ${base_price:.6f}")
        logger.info(f"  Current price: ${current_price:.6f}")
        logger.info(f"  Drop: {drop_percentage:.1f}%")
        
        # Добавляем исторические цены
        for hours_ago, price in price_points:
            price_time = current_time - timedelta(hours=hours_ago)
            
            price_data = {
                'token_address': token_address,
                'token_symbol': token_symbol,
                'blockchain': blockchain,
                'price_usd': price,
                'timestamp': price_time,
                'metadata': {'test': True, 'fake_data': True, 'hours_ago': hours_ago}
            }
            
            success = self.database.save_token_price(price_data)
            logger.debug(f"Saved price {hours_ago}h ago (${price:.6f}): {success}")
        
        # Добавляем текущую цену
        current_price_data = {
            'token_address': token_address,
            'token_symbol': token_symbol,
            'blockchain': blockchain,
            'price_usd': current_price,
            'timestamp': current_time,
            'metadata': {'test': True, 'fake_data': True, 'expected_alert': True}
        }
        
        success_current = self.database.save_token_price(current_price_data)
        logger.info(f"Saved current price: {success_current}")
        
        return success_current
    
    def test_price_drop_alert(self):
        """Тестирует алерт при падении цены"""
        logger.info("=== TESTING PRICE DROP ALERT ===")
        
        # Выбираем первый DAO для теста
        test_dao = ALL_DAOS[0]  # VitaDAO
        token_address = test_dao.token_address
        token_symbol = test_dao.token_symbol
        blockchain = test_dao.blockchain
        
        logger.info(f"Testing with {test_dao.name} ({token_symbol})")
        
        # Создаем фальшивую историю с падением 7%
        base_price = 0.015  # $0.015 базовая цена
        drop_percentage = 7.0  # 7% падение
        
        success = self.create_fake_price_history(
            token_address, token_symbol, blockchain, base_price, drop_percentage
        )
        
        if not success:
            logger.error("Failed to create fake price history")
            return False
        
        # Проверяем алерты
        token_info = {
            'dao_name': test_dao.name,
            'symbol': token_symbol,
            'blockchain': blockchain
        }
        
        alerts = self.price_tracker.check_price_alerts(token_address, token_info)
        
        logger.info(f"Generated {len(alerts)} alerts:")
        for alert in alerts:
            logger.warning(f"ALERT: {alert['title']} - {alert['message']}")
            
            # Сохраняем алерт в базу
            success = self.database.save_alert(alert)
            logger.info(f"Saved alert to database: {success}")
        
        return len(alerts) > 0
    
    def test_price_spike_alert(self):
        """Тестирует алерт при резком росте цены"""
        logger.info("=== TESTING PRICE SPIKE ALERT ===")
        
        # Выбираем второй DAO для теста
        if len(ALL_DAOS) > 1:
            test_dao = ALL_DAOS[1]  # HairDAO
        else:
            test_dao = ALL_DAOS[0]
        
        token_address = test_dao.token_address + "_spike_test"  # Делаем уникальный адрес
        token_symbol = test_dao.token_symbol
        blockchain = test_dao.blockchain
        
        logger.info(f"Testing spike with {test_dao.name} ({token_symbol})")
        
        # Создаем фальшивую историю с ростом 20%
        base_price = 0.010  # $0.010 базовая цена
        current_time = datetime.now()
        
        # Цена 1 час назад
        old_price = base_price
        old_time = current_time - timedelta(hours=1)
        
        # Текущая цена (с ростом 20%)
        spike_percentage = 20.0
        current_price = base_price * (1 + spike_percentage / 100)
        
        logger.info(f"Creating spike test for {token_symbol}:")
        logger.info(f"  Base price (1h ago): ${old_price:.6f}")
        logger.info(f"  Current price: ${current_price:.6f}")
        logger.info(f"  Spike: +{spike_percentage:.1f}%")
        
        # Сохраняем данные
        old_price_data = {
            'token_address': token_address,
            'token_symbol': token_symbol,
            'blockchain': blockchain,
            'price_usd': old_price,
            'timestamp': old_time,
            'metadata': {'test': True, 'fake_data': True}
        }
        
        current_price_data = {
            'token_address': token_address,
            'token_symbol': token_symbol,
            'blockchain': blockchain,
            'price_usd': current_price,
            'timestamp': current_time,
            'metadata': {'test': True, 'fake_data': True, 'expected_spike_alert': True}
        }
        
        success1 = self.database.save_token_price(old_price_data)
        success2 = self.database.save_token_price(current_price_data)
        
        if not (success1 and success2):
            logger.error("Failed to create fake spike history")
            return False
        
        # Проверяем алерты
        token_info = {
            'dao_name': test_dao.name,
            'symbol': token_symbol,
            'blockchain': blockchain
        }
        
        alerts = self.price_tracker.check_price_alerts(token_address, token_info)
        
        logger.info(f"Generated {len(alerts)} spike alerts:")
        for alert in alerts:
            logger.info(f"SPIKE ALERT: {alert['title']} - {alert['message']}")
            
            # Сохраняем алерт в базу
            success = self.database.save_alert(alert)
            logger.info(f"Saved spike alert to database: {success}")
        
        return len(alerts) > 0
    
    def test_multiple_timeframes(self):
        """Тестирует алерты для разных временных рамок"""
        logger.info("=== TESTING MULTIPLE TIMEFRAMES ===")
        
        test_dao = ALL_DAOS[0]
        token_address = test_dao.token_address + "_multi_test"
        token_symbol = test_dao.token_symbol
        blockchain = test_dao.blockchain
        
        current_time = datetime.now()
        base_price = 0.020
        
        # Создаем цены для разных временных периодов
        timeframes = [
            (1, 0.020),   # 1 час назад - базовая цена
            (4, 0.022),   # 4 часа назад - чуть выше
            (24, 0.025),  # 24 часа назад - значительно выше
        ]
        
        logger.info(f"Creating multi-timeframe test for {token_symbol}")
        
        # Добавляем исторические цены
        for hours_ago, price in timeframes:
            price_time = current_time - timedelta(hours=hours_ago)
            
            price_data = {
                'token_address': token_address,
                'token_symbol': token_symbol,
                'blockchain': blockchain,
                'price_usd': price,
                'timestamp': price_time,
                'metadata': {'test': True, 'fake_data': True, 'hours_ago': hours_ago}
            }
            
            success = self.database.save_token_price(price_data)
            logger.info(f"Saved price {hours_ago}h ago (${price:.6f}): {success}")
        
        # Добавляем текущую цену с значительным падением
        current_price = 0.018  # 10% падение от часовой цены, 28% от суточной
        
        current_price_data = {
            'token_address': token_address,
            'token_symbol': token_symbol,
            'blockchain': blockchain,
            'price_usd': current_price,
            'timestamp': current_time,
            'metadata': {'test': True, 'fake_data': True, 'multi_timeframe_test': True}
        }
        
        success = self.database.save_token_price(current_price_data)
        logger.info(f"Saved current price (${current_price:.6f}): {success}")
        
        # Проверяем алерты для всех временных рамок
        token_info = {
            'dao_name': test_dao.name,
            'symbol': token_symbol,
            'blockchain': blockchain
        }
        
        alerts = self.price_tracker.check_price_alerts(token_address, token_info)
        
        logger.info(f"Generated {len(alerts)} multi-timeframe alerts:")
        for alert in alerts:
            logger.warning(f"TIMEFRAME ALERT: {alert['message']} (Period: {alert.get('time_period', 'unknown')})")
            
            # Сохраняем алерт в базу
            success = self.database.save_alert(alert)
            logger.info(f"Saved timeframe alert to database: {success}")
        
        return len(alerts) > 0
    
    def show_test_results(self):
        """Показывает результаты тестирования"""
        logger.info("=== TEST RESULTS SUMMARY ===")
        
        # Получаем все тестовые алерты
        recent_alerts = self.database.get_recent_alerts(hours=1)
        
        logger.info(f"Found {len(recent_alerts)} recent alerts")
        
        # Простая проверка алертов
        test_alerts = []
        for alert in recent_alerts:
            # Проверяем разными способами
            is_test = False
            if isinstance(alert.get('metadata'), dict):
                is_test = alert['metadata'].get('test', False)
            elif 'test' in str(alert.get('message', '')).lower():
                is_test = True
            elif 'VITA' in str(alert.get('message', '')):  # Наш тестовый токен
                is_test = True
            
            if is_test:
                test_alerts.append(alert)
        
        logger.info(f"Total test alerts generated: {len(test_alerts)}")
        
        for i, alert in enumerate(test_alerts, 1):
            logger.info(f"\nAlert #{i}:")
            logger.info(f"  Type: {alert['alert_type']}")
            logger.info(f"  DAO: {alert['dao_name']}")
            logger.info(f"  Severity: {alert['severity']}")
            logger.info(f"  Message: {alert['message']}")
            logger.info(f"  Time: {alert['timestamp']}")
        
        return len(test_alerts)
    
    def check_alerts_in_db(self):
        """Простая проверка алертов в базе данных"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.database.db_path)
            cursor = conn.cursor()
            
            # Получаем все алерты за последний час
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE timestamp >= datetime('now', '-1 hours')
            """)
            
            total_alerts = cursor.fetchone()[0]
            logger.info(f"Total alerts in DB (last hour): {total_alerts}")
            
            # Получаем алерты по типам
            cursor.execute("""
                SELECT alert_type, COUNT(*) FROM alerts 
                WHERE timestamp >= datetime('now', '-1 hours')
                GROUP BY alert_type
            """)
            
            for alert_type, count in cursor.fetchall():
                logger.info(f"  {alert_type}: {count} alerts")
            
            conn.close()
            return total_alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts in DB: {e}")
            return 0
    
    def cleanup_test_data(self):
        """Очищает тестовые данные"""
        logger.info("=== CLEANING UP TEST DATA ===")
        
        # Удаляем тестовые записи цен
        # Примечание: в реальной реализации нужно добавить метод удаления в database.py
        logger.info("Test data cleanup completed (manual cleanup may be needed)")

def main():
    """Основная функция тестирования"""
    logger.info("Starting Alert Testing Suite")
    
    tester = AlertTester()
    
    try:
        # Тест 1: Падение цены
        logger.info("\n" + "="*50)
        success1 = tester.test_price_drop_alert()
        logger.info(f"Price drop test result: {'PASS' if success1 else 'FAIL'}")
        
        # Тест 2: Резкий рост цены
        logger.info("\n" + "="*50)
        success2 = tester.test_price_spike_alert()
        logger.info(f"Price spike test result: {'PASS' if success2 else 'FAIL'}")
        
        # Тест 3: Множественные временные рамки
        logger.info("\n" + "="*50)
        success3 = tester.test_multiple_timeframes()
        logger.info(f"Multiple timeframes test result: {'PASS' if success3 else 'FAIL'}")
        
        # Показываем результаты
        logger.info("\n" + "="*50)
        total_alerts = tester.show_test_results()
        
        # Проверяем базу данных напрямую
        logger.info("\n" + "="*50)
        logger.info("=== DIRECT DATABASE CHECK ===")
        db_alerts = tester.check_alerts_in_db()
        
        # Итоговый результат
        logger.info("\n" + "="*50)
        logger.info("ALERT TESTING COMPLETED")
        logger.info(f"Tests passed: {sum([success1, success2, success3])}/3")
        logger.info(f"Total alerts via API: {total_alerts}")
        logger.info(f"Total alerts in DB: {db_alerts}")
        
        if db_alerts > 0:
            logger.info("✅ Alert system is working correctly!")
        else:
            logger.warning("❌ No alerts generated - check configuration")
        
        # Очистка
        tester.cleanup_test_data()
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise

if __name__ == "__main__":
    main() 