#!/usr/bin/env python3
"""
DAO Treasury Monitor - Основной скрипт запуска
Мониторинг treasury транзакций и pool активности для BIO Protocol DAOs
"""

import asyncio
import logging
import signal
import sys
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.dao_config import print_monitoring_summary
from database.database import DAOTreasuryDatabase
from monitors.solana_monitor import SolanaMonitor
from monitors.price_tracker import PriceTracker

# Настройка логирования
def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """Настройка системы логирования"""
    
    # Определяем уровень логирования
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Настройки логирования
    logging_config = {
        'level': level,
        'format': log_format,
        'datefmt': '%Y-%m-%d %H:%M:%S'
    }
    
    # Добавляем файл логов если указан
    if log_file:
        logging_config['filename'] = log_file
        logging_config['filemode'] = 'a'
    
    logging.basicConfig(**logging_config)
    
    # Дополнительно логируем в консоль если используется файл
    if log_file:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        logging.getLogger().addHandler(console_handler)
    
    # Настраиваем логи для внешних библиотек
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

class DAOTreasuryMonitorApp:
    """Основное приложение DAO Treasury Monitor"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database = None
        self.solana_monitor = None
        self.price_tracker = None
        self.running = False
        
        # Обработчики сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # API ключи
        self.helius_api_key = get_helius_api_key()
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для завершения работы"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def initialize_database(self):
        """Инициализация базы данных"""
        try:
            self.database = DAOTreasuryDatabase()
            self.logger.info(f"Database initialized: {self.database.db_path}")
            
            # Показываем статистику базы данных
            stats = self.database.get_database_stats()
            self.logger.info(f"Database stats: {stats}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def initialize_monitors(self):
        """Инициализация мониторов"""
        try:
            # Инициализируем Solana мониторинг
            if self.helius_api_key:
                self.solana_monitor = SolanaMonitor(self.helius_api_key, self.database)
                self.logger.info("Solana monitor initialized")
            else:
                self.logger.warning("Helius API key not found - Solana monitoring disabled")
            
            # Инициализируем price tracker
            self.price_tracker = PriceTracker(self.database)
            self.logger.info("Price tracker initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitors: {e}")
            raise
    
    async def run_monitoring_cycle(self):
        """Один цикл мониторинга"""
        start_time = time.time()
        
        try:
            if self.solana_monitor:
                await self.solana_monitor.run_monitoring_cycle()
            
            duration = time.time() - start_time
            self.logger.info(f"Monitoring cycle completed in {duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
    
    async def start_monitoring(self):
        """Запуск основного мониторинга с price tracking"""
        self.logger.info("Starting DAO Treasury Monitor")
        self.running = True
        
        # Создаем задачи для параллельного выполнения
        tasks = []
        
        # Основной мониторинг транзакций
        if self.solana_monitor:
            tasks.append(asyncio.create_task(self._run_transaction_monitoring()))
        
        # Price tracking
        if self.price_tracker:
            tasks.append(asyncio.create_task(self._run_price_tracking()))
        
        if not tasks:
            self.logger.error("No monitors initialized, nothing to do")
            return
        
        try:
            # Запускаем все задачи параллельно
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Error in monitoring: {e}")
        finally:
            self.running = False
    
    async def _run_transaction_monitoring(self):
        """Запуск мониторинга транзакций"""
        self.logger.info("Starting transaction monitoring")
        
        while self.running:
            try:
                await self.run_monitoring_cycle()
                
                # Ожидание между циклами
                self.logger.debug("Waiting 30 seconds until next cycle")
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in transaction monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _run_price_tracking(self):
        """Запуск price tracking"""
        self.logger.info("Starting price tracking")
        
        while self.running:
            try:
                await self.price_tracker.run_price_tracking_cycle()
                
                # Ожидание между циклами price tracking (5 минут)
                self.logger.debug("Waiting 5 minutes until next price check")
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in price tracking: {e}")
                await asyncio.sleep(60)
    
    def run_test_mode(self):
        """Запуск в тестовом режиме"""
        self.logger.info("Running in test mode")
        
        try:
            # Тестируем подключение к базе данных
            stats = self.database.get_database_stats()
            self.logger.info(f"Database test successful: {stats}")
            
            # Тестируем получение цен токенов
            from utils.price_utils import get_bio_token_price, format_price
            
            bio_eth_price = get_bio_token_price('ethereum')
            bio_sol_price = get_bio_token_price('solana')
            
            self.logger.info(f"BIO (Ethereum) price: {format_price(bio_eth_price)}")
            self.logger.info(f"BIO (Solana) price: {format_price(bio_sol_price)}")
            
            # Тестируем Solana мониторинг
            if self.solana_monitor:
                self.logger.info("Solana monitor test: OK")
            else:
                self.logger.warning("Solana monitor not available")
            
            self.logger.info("Test mode completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Test mode failed: {e}")
            return False
    
    def run_test_alerts_mode(self):
        """Запуск тестирования алертов"""
        self.logger.info("Running alert testing mode")
        
        try:
            # Импортируем тестировщик алертов
            from test_alerts import AlertTester
            
            # Создаем тестировщик
            tester = AlertTester()
            
            # Запускаем тесты
            self.logger.info("Starting alert tests...")
            
            # Тест падения цены
            success1 = tester.test_price_drop_alert()
            self.logger.info(f"Price drop test: {'PASS' if success1 else 'FAIL'}")
            
            # Тест роста цены
            success2 = tester.test_price_spike_alert()
            self.logger.info(f"Price spike test: {'PASS' if success2 else 'FAIL'}")
            
            # Тест множественных временных рамок
            success3 = tester.test_multiple_timeframes()
            self.logger.info(f"Multiple timeframes test: {'PASS' if success3 else 'FAIL'}")
            
            # Показываем результаты
            total_alerts = tester.show_test_results()
            
            # Итоговый результат
            passed_tests = sum([success1, success2, success3])
            self.logger.info(f"Alert testing completed: {passed_tests}/3 tests passed, {total_alerts} alerts generated")
            
            if total_alerts > 0:
                self.logger.info("✅ Alert system is working correctly!")
                return True
            else:
                self.logger.warning("❌ No alerts generated - check configuration")
                return False
            
        except Exception as e:
            self.logger.error(f"Alert test mode failed: {e}")
            return False
    
    def show_status(self):
        """Показать статус системы"""
        self.logger.info("=== DAO TREASURY MONITOR STATUS ===")
        
        # Конфигурация
        print_monitoring_summary()
        
        # Статистика базы данных
        if self.database:
            stats = self.database.get_database_stats()
            print(f"\nDatabase Statistics:")
            print(f"  Treasury transactions: {stats.get('treasury_transactions', 0)}")
            print(f"  Pool activities: {stats.get('pool_activities', 0)}")
            print(f"  Balance snapshots: {stats.get('balance_snapshots', 0)}")
            print(f"  Alerts: {stats.get('alerts', 0)}")
            print(f"  Database size: {stats.get('database_size_mb', 0):.2f} MB")
        
        # Состояние мониторов
        print(f"\nMonitor Status:")
        print(f"  Solana Monitor: {'✓ Active' if self.solana_monitor else '✗ Disabled'}")
        print(f"  Ethereum Monitor: ✗ Not implemented (Stage 2)")
        
        # Переменные окружения
        print(f"\nEnvironment Variables:")
        print(f"  HELIUS_API_KEY: {'✓ Set' if os.getenv('HELIUS_API_KEY') else '✗ Not set'}")
        print(f"  COINGECKO_API_KEY: {'✓ Set' if os.getenv('COINGECKO_API_KEY') else '✓ Using default'}")

    def finalize_shutdown(self):
        """Финализация остановки приложения"""
        self.logger.info("Finalizing shutdown...")
        
        # Остановка мониторов
        if self.solana_monitor:
            # Solana monitor не требует специальной очистки
            pass
        
        if self.price_tracker:
            # Price tracker не требует специальной очистки
            pass
        
        # Закрытие базы данных
        if self.database:
            # SQLite автоматически закрывается при завершении приложения
            pass
        
        self.logger.info("Shutdown completed")
    
    async def run(self):
        """Запуск приложения"""
        try:
            self.initialize_database()
            self.initialize_monitors()
            
            # Определяем режим работы из аргументов командной строки
            parser = argparse.ArgumentParser()
            parser.add_argument('--mode', choices=['monitor', 'test', 'status', 'test-alerts'], default='monitor')
            args, unknown = parser.parse_known_args()
            
            mode = args.mode
            
            self.logger.info(f"Running in mode: {mode}")
            
            if mode == 'test':
                success = self.run_test_mode()
                if not success:
                    raise Exception("Test mode failed")
                    
            elif mode == 'test-alerts':
                success = self.run_test_alerts_mode()
                if not success:
                    raise Exception("Alert test mode failed")
                    
            elif mode == 'status':
                self.show_status()
                
            elif mode == 'monitor':
                await self.start_monitoring()
            
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            raise
        finally:
            self.finalize_shutdown()

def load_config():
    """Загрузка конфигурации"""
    return {
        'database_path': 'dao_treasury_monitor.db',
        'check_interval': 30,  # секунды
        'helius_api_key': 'd4af7b72-f199-4d77-91a9-11d8512c5e42',
        'log_level': 'INFO'
    }

def get_coingecko_api_key() -> str:
    """Получение CoinGecko API ключа"""
    return os.getenv('COINGECKO_API_KEY', 'CG-9MrJcucBMMx5HKnXeVBD8oSb')

def get_helius_api_key() -> Optional[str]:
    """Получение Helius API ключа"""
    # Пытаемся получить из переменной окружения
    api_key = os.getenv('HELIUS_API_KEY')
    if api_key:
        return api_key
    
    # Используем ключ по умолчанию из конфигурации
    return 'd4af7b72-f199-4d77-91a9-11d8512c5e42'

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='DAO Treasury Monitor')
    parser.add_argument('--mode', choices=['monitor', 'test', 'status', 'test-alerts'], 
                       default='monitor', help='Режим работы')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Уровень логирования')
    parser.add_argument('--log-file', help='Файл для логов')
    parser.add_argument('--config', help='Файл конфигурации (пока не используется)')
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger('main')
    
    logger.info("Starting DAO Treasury Monitor")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Log level: {args.log_level}")
    
    try:
        # Загрузка конфигурации
        config = load_config()
        config['log_level'] = args.log_level
        
        # Создание приложения
        app = DAOTreasuryMonitorApp(config)
        
        # Запуск приложения
        asyncio.run(app.run())
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 