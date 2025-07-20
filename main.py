#!/usr/bin/env python3
"""
BIO Whale Monitor - Основной скрипт запуска
Мониторинг крупных исходящих транзакций BIO и vBIO токенов
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

# Загружаем переменные окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.whale_config import print_whale_monitoring_summary, MONITORED_WALLETS
from database.database import DAOTreasuryDatabase
from monitors.bio_whale_monitor import BIOWhaleMonitor
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
    
    # Проверяем переменные окружения для Railway
    database_url = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')
    
    if database_url and POSTGRESQL_AVAILABLE:
        logging.info(f"Using PostgreSQL database for Railway deployment: {database_url[:50]}...")
        return PostgreSQLDatabase(database_url)
    else:
        logging.info("Using SQLite database for local development")
        return DAOTreasuryDatabase()

def get_ethereum_rpc_url() -> Optional[str]:
    """Получение Ethereum RPC URL"""
    return os.getenv('ETHEREUM_RPC_URL')

class BIOWhaleMonitorApp:
    """Основное приложение BIO Whale Monitor"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database = None
        self.whale_monitor = None
        self.notification_system = None
        self.health_server = None
        self.running = False
        
        # Обработчики сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # API ключи
        self.ethereum_rpc_url = get_ethereum_rpc_url()
    
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
            
            # Проверяем Ethereum RPC URL
            if not self.ethereum_rpc_url:
                self.logger.warning("⚠️ ETHEREUM_RPC_URL not configured - whale monitoring will be limited")
            
            # Инициализируем BIO Whale мониторинг (если есть RPC)
            if self.ethereum_rpc_url:
                try:
                    self.whale_monitor = BIOWhaleMonitor(
                        self.ethereum_rpc_url, 
                        self.database, 
                        self.notification_system
                    )
                    self.logger.info("✅ BIO Whale monitor initialized successfully")
                except Exception as e:
                    self.logger.error(f"❌ Failed to initialize BIO Whale monitor: {e}")
                    self.whale_monitor = None
            else:
                self.logger.warning("⚠️ BIO Whale monitor skipped - no Ethereum RPC URL")
                self.whale_monitor = None
            
            # Инициализируем Health Check Server (всегда)
            try:
                self.health_server = get_health_server()
                if self.health_server:
                    self.health_server.database = self.database
                    self.logger.info("✅ Health check server initialized")
                else:
                    self.logger.warning("⚠️ Health check server not available")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize health check server: {e}")
                self.health_server = None
            
        except Exception as e:
            self.logger.error(f"❌ Critical error in monitor initialization: {e}")
            import traceback
            self.logger.error(f"Monitor initialization traceback: {traceback.format_exc()}")
            # Не поднимаем исключение - пусть система попробует работать
    
    async def _send_deployment_notification_async(self):
        """Асинхронная отправка уведомления о успешном деплое"""
        try:
            self.logger.info("🚀 Preparing deployment notification...")
            
            # Проверяем статус мониторинга
            whale_status = "✅ Active" if self.whale_monitor else "❌ Disabled"
            wallets_count = len(MONITORED_WALLETS)
            
            # Статистика базы данных
            stats = self.database.get_database_stats()
            
            message = f"""🚀 **BIO Whale Monitor Deployed Successfully**

🐋 **Whale Monitor Status:** {whale_status}
👛 **Monitored Wallets:** {wallets_count}
📊 **Health Check:** ✅ Active

**Database Stats:**
• Transactions: {stats.get('treasury_transactions', 0)}
• Alerts: {stats.get('alerts', 0)}
• DB Size: {stats.get('database_size_mb', 0):.2f} MB

**Monitoring Thresholds:**
• Token Amount: 1,000,000+ BIO/vBIO
• USD Value: $100,000+
• Check Interval: 30 seconds

🎯 Whale monitoring is active 24/7!"""
            
            # Отправляем уведомление
            if hasattr(self.notification_system, 'telegram') and self.notification_system.telegram:
                success = await self.notification_system.telegram.send_message(message)
                if success:
                    self.logger.info("🎉 Deployment notification sent to Telegram successfully")
                else:
                    self.logger.warning("❌ Failed to send deployment notification to Telegram")
            else:
                self.logger.warning("❌ Telegram bot not configured - deployment notification skipped")
                
        except Exception as e:
            self.logger.error(f"❌ Error sending deployment notification: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    async def run_whale_monitoring_cycle(self):
        """Один цикл whale мониторинга"""
        start_time = time.time()
        
        try:
            self.logger.info("Starting whale monitoring cycle")
            
            # Запускаем whale мониторинг
            if self.whale_monitor:
                self.logger.info("Running whale monitoring...")
                await self.whale_monitor.run_whale_monitoring_cycle()
            else:
                self.logger.warning("Whale monitor not available")
            
            # Обновляем время активности для health check
            if self.health_server:
                self.health_server.update_activity_time()
            
            duration = time.time() - start_time
            self.logger.info(f"Whale monitoring cycle completed in {duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in whale monitoring cycle: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    async def start_monitoring(self):
        """Запуск основного whale мониторинга"""
        self.logger.info("🚀 Starting BIO Whale Monitor")
        self.running = True
        
        # Railway environment диагностика
        railway_env = os.getenv('RAILWAY_ENVIRONMENT', 'local')
        port = os.getenv('PORT', '8080')  # Fallback для Railway
        database_url = os.getenv('DATABASE_URL')
        telegram_bot = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat = os.getenv('TELEGRAM_CHAT_ID')
        ethereum_rpc = os.getenv('ETHEREUM_RPC_URL')
        
        self.logger.info(f"📊 ENVIRONMENT DIAGNOSTICS:")
        self.logger.info(f"   Environment: {railway_env}")
        self.logger.info(f"   Port: {port}")
        self.logger.info(f"   Database URL: {'✅ Set' if database_url else '❌ Not set'}")
        self.logger.info(f"   Telegram Bot: {'✅ Set' if telegram_bot else '❌ Not set'}")
        self.logger.info(f"   Telegram Chat: {'✅ Set' if telegram_chat else '❌ Not set'}")
        self.logger.info(f"   Ethereum RPC: {'✅ Set' if ethereum_rpc else '❌ Not set'}")
        self.logger.info(f"   Health server: {'✅ Available' if self.health_server else '❌ Not available'}")
        
        # Отправляем уведомление о деплое в Railway
        if railway_env == 'production' and self.notification_system:
            await self._send_deployment_notification_async()
        
        # Создаем задачи для параллельного выполнения
        tasks = []
        
        # Health check server (для Railway) - запускаем ВСЕГДА если есть PORT
        if self.health_server and port:
            try:
                port_int = int(port)
                self.health_server.port = port_int
                self.logger.info(f"🏥 Preparing health check server on 0.0.0.0:{port_int}")
                
                # Запускаем health check server в отдельной задаче
                tasks.append(asyncio.create_task(self._run_health_server()))
            except ValueError:
                self.logger.error(f"❌ Invalid PORT value: {port}")
        else:
            self.logger.warning("⚠️ Health check server not available or PORT not set")
        
        # Whale мониторинг - только если есть Ethereum RPC
        if self.whale_monitor and ethereum_rpc:
            self.logger.info("🐋 Preparing whale monitoring task")
            tasks.append(asyncio.create_task(self._run_whale_monitoring()))
        elif not ethereum_rpc:
            self.logger.warning("⚠️ ETHEREUM_RPC_URL not set - whale monitoring disabled")
        
        if not tasks:
            self.logger.error("❌ No monitoring tasks could be initialized")
            # В Railway должен быть хотя бы health check
            if railway_env == 'production':
                self.logger.info("🏥 Starting minimal health server for Railway...")
                await self._run_minimal_health_server()
            return
        
        self.logger.info(f"🚀 Starting {len(tasks)} parallel tasks...")
        
        try:
            # Запускаем все задачи параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Проверяем результаты
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"❌ Task {i} failed: {result}")
                    
        except Exception as e:
            self.logger.error(f"❌ Critical error in monitoring: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            self.running = False
            self.logger.info("🔄 Monitoring stopped")
    
    async def _run_health_server(self):
        """Запуск health check сервера"""
        try:
            self.logger.info(f"🏥 Health check server starting...")
            await self.health_server.start_server()
        except Exception as e:
            self.logger.error(f"❌ Health check server failed: {e}")
            import traceback
            self.logger.error(f"Health check traceback: {traceback.format_exc()}")
    
    async def _run_whale_monitoring(self):
        """Запуск whale мониторинга"""
        self.logger.info("🐋 Starting whale monitoring thread")
        
        while self.running:
            try:
                self.logger.info("🐋 Running whale monitoring cycle...")
                await self.run_whale_monitoring_cycle()
                self.logger.info("✅ Whale monitoring cycle completed")
                
                # Ожидание между циклами (настраивается в конфиге)
                from config.whale_config import MONITORING_CONFIG
                check_interval = MONITORING_CONFIG['check_interval']
                self.logger.info(f"⏰ Waiting {check_interval} seconds until next whale check")
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Error in whale monitoring: {e}")
                import traceback
                self.logger.error(f"Whale monitoring traceback: {traceback.format_exc()}")
                self.logger.info("🔄 Retrying whale monitoring in 60 seconds...")
                await asyncio.sleep(60)
    
    async def _run_minimal_health_server(self):
        """Запуск минимального health сервера для Railway"""
        try:
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse
            import uvicorn
            
            port = int(os.getenv('PORT', 8080))
            app = FastAPI(title="BIO Whale Monitor Health")
            
            @app.get("/health")
            async def health():
                return JSONResponse({"status": "healthy", "service": "bio-whale-monitor"})
            
            self.logger.info(f"🏥 Starting minimal health server on port {port}")
            
            config = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"❌ Minimal health server failed: {e}")
    
    def run_test_mode(self):
        """Запуск в тестовом режиме"""
        self.logger.info("Running in test mode")
        
        try:
            # Тестируем подключение к базе данных
            stats = self.database.get_database_stats()
            database_type = "PostgreSQL" if hasattr(self.database, 'connection_pool') else "SQLite"
            self.logger.info(f"Database test successful ({database_type}): {stats}")
            
            # Тестируем получение цен BIO токенов
            from utils.price_utils import get_bio_token_price, format_price
            
            bio_price = get_bio_token_price('ethereum')
            self.logger.info(f"BIO token price: {format_price(bio_price)}")
            
            # Проверяем конфигурацию whale мониторинга
            if self.whale_monitor:
                whale_stats = self.whale_monitor.get_monitoring_stats()
                self.logger.info(f"Whale monitoring stats: {whale_stats}")
            
            self.logger.info("✅ Test mode completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Test mode failed: {e}")
            import traceback
            self.logger.error(f"Test traceback: {traceback.format_exc()}")
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
        self.logger.info("=== BIO WHALE MONITOR STATUS ===")
        
        # Конфигурация
        print_whale_monitoring_summary()
        
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
        print(f"  Whale Monitor: {'✓ Active' if self.whale_monitor else '✗ Disabled'}")
        print(f"  Health Check Server: {'✓ Available' if self.health_server else '✗ Disabled'}")
        
        # Переменные окружения
        print(f"\nEnvironment Variables:")
        print(f"  ETHEREUM_RPC_URL: {'✓ Set' if self.ethereum_rpc_url else '✗ Not set'}")
        print(f"  RAILWAY_ENVIRONMENT: {'✓ Set' if os.getenv('RAILWAY_ENVIRONMENT') else '✗ Not set'}")
        print(f"  PORT: {'✓ Set' if os.getenv('PORT') else '✗ Not set'}")

    def finalize_shutdown(self):
        """Финализация остановки приложения"""
        self.logger.info("Finalizing shutdown...")
        
        # Остановка мониторов
        if self.whale_monitor:
            # Whale monitor не требует специальной очистки
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

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='BIO Whale Monitor')
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
    
    logger.info("Starting BIO Whale Monitor")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Log level: {args.log_level}")
    
    try:
        # Загрузка конфигурации
        config = load_config()
        config['log_level'] = args.log_level
        
        # Создание приложения
        app = BIOWhaleMonitorApp(config)
        
        # Запуск приложения
        asyncio.run(app.run())
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 