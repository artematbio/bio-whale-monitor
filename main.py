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
# Добавляем Ethereum мониторинг
from monitors.ethereum_monitor import EthereumMonitor
from notifications.notification_system import NotificationSystem, init_notification_system
from health_check import get_health_server

# Добавляем PostgreSQL поддержку для Railway
try:
    from database.postgresql_database import PostgreSQLDatabase
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

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

def get_database():
    """Получение экземпляра базы данных (SQLite или PostgreSQL)"""
    
    # Проверяем переменную окружения для Railway
    database_url = os.getenv('DATABASE_URL')
    
    if database_url and POSTGRESQL_AVAILABLE:
        logging.info("Using PostgreSQL database for Railway deployment")
        return PostgreSQLDatabase(database_url)
    else:
        logging.info("Using SQLite database for local development")
        return DAOTreasuryDatabase()

class DAOTreasuryMonitorApp:
    """Основное приложение DAO Treasury Monitor"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database = None
        self.solana_monitor = None
        self.ethereum_monitor = None  # Добавляем Ethereum мониторинг
        self.price_tracker = None
        self.notification_system = None
        self.health_server = None
        self.running = False
        
        # Обработчики сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # API ключи
        self.helius_api_key = get_helius_api_key()
        self.ethereum_rpc_url = get_ethereum_rpc_url()  # Добавляем Ethereum RPC
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для завершения работы"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def initialize_database(self):
        """Инициализация базы данных"""
        try:
            self.database = get_database()
            database_type = "PostgreSQL" if hasattr(self.database, 'connection_pool') else "SQLite"
            self.logger.info(f"Database initialized: {database_type}")
            
            # Показываем статистику базы данных
            stats = self.database.get_database_stats()
            self.logger.info(f"Database stats: {stats}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def initialize_monitors(self):
        """Инициализация мониторов"""
        try:
            # Инициализируем систему уведомлений
            self.notification_system = init_notification_system(self.database)
            self.logger.info("Notification system initialized")
            
            # Инициализируем Solana мониторинг
            if self.helius_api_key:
                self.solana_monitor = SolanaMonitor(self.helius_api_key, self.database)
                self.logger.info("Solana monitor initialized")
            else:
                self.logger.warning("Helius API key not found - Solana monitoring disabled")
            
            # Подробная диагностика Ethereum мониторинга
            self.logger.info("=== ETHEREUM MONITORING DIAGNOSTICS ===")
            self.logger.info(f"ETHEREUM_RPC_URL env var: {os.getenv('ETHEREUM_RPC_URL')}")
            self.logger.info(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT')}")
            self.logger.info(f"self.ethereum_rpc_url: {self.ethereum_rpc_url}")
            self.logger.info(f"get_ethereum_rpc_url() result: {get_ethereum_rpc_url()}")
            
            # Инициализируем Ethereum мониторинг с диагностикой
            self.logger.info(f"Checking Ethereum RPC URL: {self.ethereum_rpc_url}")
            if self.ethereum_rpc_url:
                try:
                    self.ethereum_monitor = EthereumMonitor(self.ethereum_rpc_url, self.database)
                    self.logger.info("✅ Ethereum monitor initialized successfully")
                except Exception as e:
                    self.logger.error(f"❌ Failed to initialize Ethereum monitor: {e}")
                    import traceback
                    self.logger.error(f"Full traceback: {traceback.format_exc()}")
                    self.ethereum_monitor = None
            else:
                self.logger.warning("❌ Ethereum RPC URL not found - Ethereum monitoring disabled")
                self.logger.info(f"   ETHEREUM_RPC_URL env var: {os.getenv('ETHEREUM_RPC_URL')}")
                self.logger.info(f"   RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT')}")
            
            self.logger.info("=== END ETHEREUM DIAGNOSTICS ===")
            
            # Инициализируем price tracker
            self.price_tracker = PriceTracker(self.database)
            self.logger.info("Price tracker initialized")
            
            # Инициализируем health check server для Railway
            self.health_server = get_health_server()
            self.logger.info("Health check server initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitors: {e}")
            raise
    
    async def run_monitoring_cycle(self):
        """Один цикл мониторинга"""
        start_time = time.time()
        
        try:
            self.logger.info("Starting monitoring cycle")
            
            # Запускаем Solana мониторинг
            if self.solana_monitor:
                self.logger.info("Running Solana monitoring...")
                await self.solana_monitor.run_monitoring_cycle()
            else:
                self.logger.warning("Solana monitor not available")
            
            # Запускаем Ethereum мониторинг
            if self.ethereum_monitor:
                self.logger.info("Running Ethereum monitoring...")
                await self.ethereum_monitor.monitor_treasury_addresses()
            else:
                self.logger.warning("Ethereum monitor not available")
            
            # Обновляем время активности для health check
            if self.health_server:
                self.health_server.update_activity_time()
            
            duration = time.time() - start_time
            self.logger.info(f"Monitoring cycle completed in {duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    async def start_monitoring(self):
        """Запуск основного мониторинга с price tracking и health check"""
        self.logger.info("Starting DAO Treasury Monitor")
        self.running = True
        
        # Создаем задачи для параллельного выполнения
        tasks = []
        
        # Health check server (для Railway)
        if self.health_server and os.getenv('PORT'):
            port = int(os.getenv('PORT', 8080))
            self.health_server.port = port
            tasks.append(asyncio.create_task(self.health_server.start_server()))
            self.logger.info(f"Health check server will start on port {port}")
        
        # Основной мониторинг транзакций
        if self.solana_monitor or self.ethereum_monitor:
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
            database_type = "PostgreSQL" if hasattr(self.database, 'connection_pool') else "SQLite"
            self.logger.info(f"Database test successful ({database_type}): {stats}")
            
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
            
            # Тестируем Ethereum мониторинг
            if self.ethereum_monitor:
                self.logger.info("Ethereum monitor test: OK")
            else:
                self.logger.warning("Ethereum monitor not available")
            
            # Тестируем health check
            if self.health_server:
                self.logger.info("Health check server: OK")
            
            self.logger.info("Test mode completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Test mode failed: {e}")
            return False
    
    async def run_test_alerts_mode(self):
        """Запуск тестирования алертов с Telegram уведомлениями"""
        self.logger.info("Running alert testing mode with Telegram notifications")
        
        try:
            # Тестируем систему уведомлений
            if self.notification_system:
                self.logger.info("Testing notification system...")
                
                # Тест подключения к Telegram
                telegram_results = await self.notification_system.test_notifications()
                self.logger.info(f"Telegram test results: {telegram_results}")
                
                # Создаем тестовые алерты для отправки в Telegram
                
                # 1. Тестовый алерт транзакции
                test_transaction = {
                    'dao_name': 'VitaDAO',
                    'amount_usd': 15000.50,
                    'tx_hash': '4x8Zn2kP9rF5tM3qW7yE1L6sB8vC9dH0jN4oQ2aR7uY3mK5xG1',
                    'timestamp': datetime.now(),
                    'blockchain': 'solana',
                    'token_symbol': 'VITA',
                    'amount': 1500000.0,
                    'tx_type': 'outgoing',
                    'from_address': 'GTuVLSN4cKvrWnWFbyyQX6VW14SLhfu7sjM4MrzFoj3s',
                    'to_address': '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM'
                }
                
                success1 = await self.notification_system.send_transaction_alert(test_transaction)
                self.logger.info(f"Transaction alert sent to Telegram: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
                
                # 2. Тестовый ценовой алерт
                test_price_alert = {
                    'alert_type': 'price_drop',
                    'dao_name': 'VitaDAO',
                    'token_symbol': 'VITA',
                    'title': 'Price Drop Alert - VITA',
                    'message': 'VITA price dropped 8.5% in 1h',
                    'change_percentage': -8.5,
                    'period_hours': 1,
                    'blockchain': 'ethereum',
                    'token_address': '0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321',
                    'timestamp': datetime.now()
                }
                
                success2 = await self.notification_system.send_price_alert(test_price_alert)
                self.logger.info(f"Price alert sent to Telegram: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
                
                # 3. Тест ежедневной сводки
                success3 = await self.notification_system.send_daily_summary()
                self.logger.info(f"Daily summary sent to Telegram: {'✅ SUCCESS' if success3 else '❌ FAILED'}")
                
                # Результаты
                passed_tests = sum([success1, success2, success3])
                total_tests = 3
                
                self.logger.info(f"Telegram alert testing completed: {passed_tests}/{total_tests} tests passed")
                
                if passed_tests > 0:
                    self.logger.info("🎉 Telegram notifications are working!")
                    return True
                else:
                    self.logger.warning("❌ No Telegram notifications were sent")
                    return False
            else:
                self.logger.error("Notification system not initialized")
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
            database_type = "PostgreSQL" if hasattr(self.database, 'connection_pool') else "SQLite"
            print(f"\nDatabase ({database_type}) Statistics:")
            print(f"  Treasury transactions: {stats.get('treasury_transactions', 0)}")
            print(f"  Pool activities: {stats.get('pool_activities', 0)}")
            print(f"  Balance snapshots: {stats.get('balance_snapshots', 0)}")
            print(f"  Alerts: {stats.get('alerts', 0)}")
            print(f"  Database size: {stats.get('database_size_mb', 0):.2f} MB")
        
        # Состояние мониторов
        print(f"\nMonitor Status:")
        print(f"  Solana Monitor: {'✓ Active' if self.solana_monitor else '✗ Disabled'}")
        print(f"  Ethereum Monitor: {'✓ Active' if self.ethereum_monitor else '✗ Disabled'}")
        print(f"  Health Check Server: {'✓ Available' if self.health_server else '✗ Disabled'}")
        
        # Переменные окружения
        print(f"\nEnvironment Variables:")
        print(f"  HELIUS_API_KEY: {'✓ Set' if os.getenv('HELIUS_API_KEY') else '✗ Not set'}")
        print(f"  COINGECKO_API_KEY: {'✓ Set' if os.getenv('COINGECKO_API_KEY') else '✓ Using default'}")
        print(f"  TELEGRAM_BOT_TOKEN: {'✓ Set' if os.getenv('TELEGRAM_BOT_TOKEN') else '✗ Not set'}")
        print(f"  TELEGRAM_CHAT_ID: {'✓ Set' if os.getenv('TELEGRAM_CHAT_ID') else '✗ Not set'}")
        print(f"  DATABASE_URL: {'✓ Set (PostgreSQL)' if os.getenv('DATABASE_URL') else '✗ Not set (using SQLite)'}")
        print(f"  PORT: {'✓ Set' if os.getenv('PORT') else '✗ Not set'}")

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
            if hasattr(self.database, 'close'):
                self.database.close()
        
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
                success = await self.run_test_alerts_mode()
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

def get_ethereum_rpc_url() -> Optional[str]:
    """Получение Ethereum RPC URL"""
    # Пытаемся получить из переменной окружения
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    if rpc_url:
        return rpc_url
    
    # Временный фикс для Railway - используем hardcoded URL если в Railway
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return 'https://eth-mainnet.g.alchemy.com/v2/0l42UZmHRHWXBYMJ2QFcdEE-Glj20xqn'
    
    # Для локальной разработки используем предоставленный Alchemy URL
    if not os.getenv('RAILWAY_ENVIRONMENT'):
        return 'https://eth-mainnet.g.alchemy.com/v2/0l42UZmHRHWXBYMJ2QFcdEE-Glj20xqn'
    
    # В Railway без ETHEREUM_RPC_URL возвращаем None
    return None

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