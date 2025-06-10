#!/usr/bin/env python3
"""
Notification System для DAO Treasury Monitor
Центральная система для управления всеми видами уведомлений
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal

from database.database import DAOTreasuryDatabase
from .telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)

class NotificationSystem:
    """Центральная система уведомлений"""
    
    def __init__(self, database: DAOTreasuryDatabase):
        self.database = database
        self.telegram = None
        self.notification_history = []
        
        # Настройки
        self.rate_limit_seconds = 30  # Минимальный интервал между однотипными алертами
        self.max_alerts_per_hour = 20  # Максимум алертов в час
        
        # Инициализация Telegram
        self._init_telegram()
        
        logger.info(f"Notification system initialized")
    
    def _init_telegram(self):
        """Инициализация Telegram уведомлений"""
        try:
            # Получаем настройки из переменных окружения
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if bot_token and chat_id:
                self.telegram = TelegramNotifier(bot_token, chat_id)
                if self.telegram.enabled:
                    logger.info("Telegram notifications enabled")
                else:
                    logger.warning("Failed to initialize Telegram notifications")
                    self.telegram = None
            else:
                logger.info("Telegram credentials not provided - notifications disabled")
                self.telegram = None
                
        except Exception as e:
            logger.error(f"Error initializing Telegram: {e}")
            self.telegram = None
    
    def is_rate_limited(self, alert_type: str, dao_name: str) -> bool:
        """Проверяет rate limiting для алертов"""
        try:
            current_time = datetime.now()
            
            # Проверяем лимит по типу алерта и DAO
            recent_alerts = [
                alert for alert in self.notification_history
                if (current_time - alert['timestamp']).total_seconds() < self.rate_limit_seconds
                and alert['alert_type'] == alert_type
                and alert['dao_name'] == dao_name
            ]
            
            if recent_alerts:
                logger.debug(f"Rate limited: {alert_type} for {dao_name}")
                return True
            
            # Проверяем общий лимит алертов в час
            hour_ago = current_time - timedelta(hours=1)
            recent_hour_alerts = [
                alert for alert in self.notification_history
                if alert['timestamp'] > hour_ago
            ]
            
            if len(recent_hour_alerts) >= self.max_alerts_per_hour:
                logger.warning(f"Hourly alert limit reached: {len(recent_hour_alerts)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
    def add_to_history(self, alert_data: Dict[str, Any]):
        """Добавляет алерт в историю для rate limiting"""
        try:
            history_entry = {
                'timestamp': datetime.now(),
                'alert_type': alert_data.get('alert_type', 'unknown'),
                'dao_name': alert_data.get('dao_name', 'unknown'),
                'amount_usd': alert_data.get('amount_usd', 0)
            }
            
            self.notification_history.append(history_entry)
            
            # Очищаем старую историю (больше 24 часов)
            day_ago = datetime.now() - timedelta(hours=24)
            self.notification_history = [
                alert for alert in self.notification_history
                if alert['timestamp'] > day_ago
            ]
            
        except Exception as e:
            logger.error(f"Error adding to history: {e}")
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Отправляет алерт через все подключенные каналы"""
        try:
            alert_type = alert_data.get('alert_type', 'unknown')
            dao_name = alert_data.get('dao_name', 'unknown')
            
            # Проверяем rate limiting
            if self.is_rate_limited(alert_type, dao_name):
                logger.debug(f"Alert rate limited: {alert_type} - {dao_name}")
                return False
            
            # Добавляем timestamp если не указан
            if 'timestamp' not in alert_data:
                alert_data['timestamp'] = datetime.now()
            
            success = False
            
            # Отправляем в Telegram
            if self.telegram:
                try:
                    telegram_success = await self.telegram.send_alert(alert_data)
                    if telegram_success:
                        success = True
                        # Обновляем статус в базе данных
                        await self._update_alert_status(alert_data, 'telegram', True)
                except Exception as e:
                    logger.error(f"Telegram alert failed: {e}")
                    await self._update_alert_status(alert_data, 'telegram', False)
            
            # Добавляем в историю для rate limiting
            if success:
                self.add_to_history(alert_data)
                logger.info(f"Alert sent successfully: {alert_type} - {dao_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    async def _update_alert_status(self, alert_data: Dict[str, Any], 
                                  notification_type: str, success: bool):
        """Обновляет статус отправки уведомления в базе данных"""
        try:
            # Находим алерт в базе по хэшу транзакции или другим уникальным полям
            tx_hash = alert_data.get('tx_hash')
            if tx_hash:
                # Обновляем статус в базе данных
                # Примечание: нужно добавить метод update_alert_status в database.py
                logger.debug(f"Updated {notification_type} status for {tx_hash}: {success}")
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
    
    async def send_transaction_alert(self, transaction_data: Dict[str, Any]) -> bool:
        """Отправляет алерт о крупной транзакции"""
        try:
            # Формируем данные алерта
            alert_data = {
                'alert_type': 'large_transaction',
                'dao_name': transaction_data.get('dao_name', 'Unknown DAO'),
                'severity': self._get_transaction_severity(transaction_data.get('amount_usd', 0)),
                'title': f"Large Transaction - {transaction_data.get('dao_name', 'Unknown DAO')}",
                'message': self._format_transaction_message(transaction_data),
                'tx_hash': transaction_data.get('tx_hash'),
                'amount_usd': transaction_data.get('amount_usd', 0),
                'timestamp': transaction_data.get('timestamp', datetime.now()),
                'metadata': {
                    'blockchain': transaction_data.get('blockchain', 'unknown'),
                    'token_symbol': transaction_data.get('token_symbol', 'UNKNOWN'),
                    'token_amount': transaction_data.get('amount', 0),
                    'tx_type': transaction_data.get('tx_type', 'unknown'),
                    'from_address': transaction_data.get('from_address', ''),
                    'to_address': transaction_data.get('to_address', '')
                }
            }
            
            return await self.send_alert(alert_data)
            
        except Exception as e:
            logger.error(f"Error sending transaction alert: {e}")
            return False
    
    async def send_price_alert(self, price_data: Dict[str, Any]) -> bool:
        """Отправляет ценовой алерт"""
        try:
            alert_data = {
                'alert_type': price_data.get('alert_type', 'price_change'),
                'dao_name': price_data.get('dao_name', 'Unknown DAO'),
                'severity': self._get_price_severity(price_data.get('change_percentage', 0)),
                'title': price_data.get('title', 'Price Alert'),
                'message': price_data.get('message', ''),
                'token_symbol': price_data.get('token_symbol', 'TOKEN'),
                'timestamp': price_data.get('timestamp', datetime.now()),
                'metadata': {
                    'blockchain': price_data.get('blockchain', 'unknown'),
                    'change_percentage': price_data.get('change_percentage', 0),
                    'period_hours': price_data.get('period_hours', 0),
                    'token_address': price_data.get('token_address', '')
                }
            }
            
            return await self.send_alert(alert_data)
            
        except Exception as e:
            logger.error(f"Error sending price alert: {e}")
            return False
    
    def _get_transaction_severity(self, amount_usd: float) -> str:
        """Определяет критичность транзакции по сумме"""
        if amount_usd >= 100000:  # $100K+
            return 'critical'
        elif amount_usd >= 50000:  # $50K+
            return 'high'
        elif amount_usd >= 25000:  # $25K+
            return 'medium'
        else:
            return 'low'
    
    def _get_price_severity(self, change_percentage: float) -> str:
        """Определяет критичность ценового изменения"""
        abs_change = abs(change_percentage)
        if abs_change >= 20:  # 20%+
            return 'high'
        elif abs_change >= 10:  # 10%+
            return 'medium'
        else:
            return 'low'
    
    def _format_transaction_message(self, transaction_data: Dict[str, Any]) -> str:
        """Форматирует сообщение о транзакции"""
        try:
            tx_type = transaction_data.get('tx_type', 'unknown')
            amount = transaction_data.get('amount', 0)
            token_symbol = transaction_data.get('token_symbol', 'TOKEN')
            amount_usd = transaction_data.get('amount_usd', 0)
            blockchain = transaction_data.get('blockchain', 'unknown')
            
            direction = "outgoing" if tx_type == 'outgoing' else "incoming"
            
            message = f"{direction.title()} transfer of {amount:,.2f} {token_symbol} (${amount_usd:,.2f}) on {blockchain.title()}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting transaction message: {e}")
            return "Large transaction detected"
    
    async def send_daily_summary(self) -> bool:
        """Отправляет ежедневную сводку"""
        try:
            if not self.telegram:
                logger.debug("Telegram not available for daily summary")
                return False
            
            # Получаем данные за последние 24 часа
            summary_data = await self._generate_daily_summary()
            
            if summary_data['total_transactions'] == 0:
                logger.info("No transactions in the last 24h, skipping daily summary")
                return False
            
            return await self.telegram.send_daily_summary(summary_data)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False
    
    async def _generate_daily_summary(self) -> Dict[str, Any]:
        """Генерирует данные для ежедневной сводки"""
        try:
            # Получаем транзакции за последние 24 часа
            recent_transactions = self.database.get_recent_treasury_transactions(hours=24)
            
            total_volume = sum(tx.get('amount_usd', 0) for tx in recent_transactions)
            
            # Группируем по DAO
            dao_activity = {}
            for tx in recent_transactions:
                dao_name = tx.get('dao_name', 'Unknown')
                if dao_name not in dao_activity:
                    dao_activity[dao_name] = {
                        'dao_name': dao_name,
                        'transaction_count': 0,
                        'volume_usd': 0
                    }
                dao_activity[dao_name]['transaction_count'] += 1
                dao_activity[dao_name]['volume_usd'] += tx.get('amount_usd', 0)
            
            # Сортируем по объему
            active_daos = sorted(dao_activity.values(), 
                               key=lambda x: x['volume_usd'], reverse=True)
            
            # Топ транзакции
            top_transactions = sorted(recent_transactions, 
                                    key=lambda x: x.get('amount_usd', 0), reverse=True)[:5]
            
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_transactions': len(recent_transactions),
                'total_volume_usd': total_volume,
                'active_daos': active_daos,
                'top_transactions': top_transactions
            }
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_transactions': 0,
                'total_volume_usd': 0,
                'active_daos': [],
                'top_transactions': []
            }
    
    async def test_notifications(self) -> Dict[str, bool]:
        """Тестирует все системы уведомлений"""
        results = {}
        
        try:
            # Тест Telegram
            if self.telegram:
                telegram_test = await self.telegram.test_connection()
                if telegram_test:
                    message_test = await self.telegram.send_test_message()
                    results['telegram'] = message_test
                else:
                    results['telegram'] = False
            else:
                results['telegram'] = False
                logger.info("Telegram not configured")
            
            # Можно добавить тесты для других систем уведомлений
            # results['discord'] = await self.test_discord()
            # results['email'] = await self.test_email()
            
            return results
            
        except Exception as e:
            logger.error(f"Error testing notifications: {e}")
            return {'error': True}
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Возвращает статистику уведомлений"""
        try:
            current_time = datetime.now()
            
            # Статистика за последний час
            hour_ago = current_time - timedelta(hours=1)
            recent_alerts = [
                alert for alert in self.notification_history
                if alert['timestamp'] > hour_ago
            ]
            
            # Статистика за последние 24 часа
            day_ago = current_time - timedelta(hours=24)
            daily_alerts = [
                alert for alert in self.notification_history
                if alert['timestamp'] > day_ago
            ]
            
            return {
                'alerts_last_hour': len(recent_alerts),
                'alerts_last_24h': len(daily_alerts),
                'rate_limit_active': len(recent_alerts) >= self.max_alerts_per_hour,
                'telegram_enabled': self.telegram is not None and self.telegram.enabled,
                'history_size': len(self.notification_history)
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {'error': True}

# Глобальный экземпляр системы уведомлений
_notification_system = None

def get_notification_system(database: Optional[DAOTreasuryDatabase] = None) -> Optional[NotificationSystem]:
    """Получает глобальный экземпляр системы уведомлений"""
    global _notification_system
    if _notification_system is None and database is not None:
        _notification_system = NotificationSystem(database)
    return _notification_system

def init_notification_system(database: DAOTreasuryDatabase) -> NotificationSystem:
    """Инициализирует глобальную систему уведомлений"""
    global _notification_system
    _notification_system = NotificationSystem(database)
    return _notification_system 