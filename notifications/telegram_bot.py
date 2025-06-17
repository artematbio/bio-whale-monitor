#!/usr/bin/env python3
"""
Telegram Bot для DAO Treasury Monitor
Отправляет уведомления о крупных транзакциях и ценовых изменениях
"""

import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

from telegram import Bot
from telegram.error import TelegramError
import httpx

# Настройка логирования
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        # Получаем настройки из переменных окружения или параметров
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        # Проверяем наличие обязательных настроек
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set - Telegram notifications disabled")
            self.enabled = False
            return
        
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not set - Telegram notifications disabled")
            self.enabled = False
            return
        
        # Инициализируем бота
        try:
            self.bot = Bot(token=self.bot_token)
            self.enabled = True
            logger.info(f"Telegram notifier initialized for chat: {self.chat_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.enabled = False
    
    async def test_connection(self) -> bool:
        """Тестирует подключение к Telegram API"""
        if not self.enabled:
            return False
        
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot connected: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    def format_transaction_alert(self, alert_data: Dict[str, Any]) -> str:
        """Форматирует алерт о транзакции для Telegram"""
        try:
            # Основная информация
            dao_name = alert_data.get('dao_name', 'Unknown DAO')
            amount_usd = alert_data.get('amount_usd', 0)
            tx_hash = alert_data.get('tx_hash', '')
            severity = alert_data.get('severity', 'medium')
            
            # Эмодзи в зависимости от критичности
            severity_emoji = {
                'low': '🟢',
                'medium': '🟡', 
                'high': '🔴',
                'critical': '🚨'
            }.get(severity, '⚠️')
            
            # Базовая структура сообщения
            message = f"{severity_emoji} **{alert_data.get('title', 'Treasury Alert')}**\n\n"
            message += f"🏛️ **DAO:** {dao_name}\n"
            message += f"💰 **Amount:** ${amount_usd:,.2f}\n"
            
            # Дополнительные данные из metadata
            metadata = alert_data.get('metadata', {})
            if isinstance(metadata, dict):
                if 'token_symbol' in metadata:
                    token_amount = metadata.get('token_amount', 0)
                    token_symbol = metadata.get('token_symbol', '')
                    message += f"🪙 **Token:** {token_amount:,.2f} {token_symbol}\n"
                
                if 'blockchain' in metadata:
                    message += f"⛓️ **Chain:** {metadata['blockchain'].title()}\n"
                
                if 'tx_type' in metadata:
                    tx_type = metadata['tx_type']
                    direction_emoji = '📤' if tx_type == 'outgoing' else '📥'
                    message += f"{direction_emoji} **Type:** {tx_type.title()}\n"
            
            # Время
            timestamp = alert_data.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, datetime):
                    pass
                message += f"⏰ **Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            
            # Хэш транзакции (сокращенный)
            if tx_hash:
                short_hash = f"{tx_hash[:8]}...{tx_hash[-8:]}" if len(tx_hash) > 20 else tx_hash
                message += f"🔗 **TX:** `{short_hash}`\n"
            
            # Описание
            description = alert_data.get('message', '')
            if description:
                message += f"\n📝 **Details:** {description}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting transaction alert: {e}")
            return f"⚠️ Alert formatting error: {alert_data.get('title', 'Unknown alert')}"
    
    def format_price_alert(self, alert_data: Dict[str, Any]) -> str:
        """Форматирует ценовой алерт для Telegram"""
        try:
            dao_name = alert_data.get('dao_name', 'Unknown DAO')
            token_symbol = alert_data.get('token_symbol', 'TOKEN')
            alert_type = alert_data.get('alert_type', 'price_change')
            
            # Определяем эмодзи и цвет по типу алерта
            if alert_type == 'price_drop':
                emoji = '📉'
                color = '🔴'
            elif alert_type == 'price_spike':
                emoji = '📈'
                color = '🟢'
            else:
                emoji = '📊'
                color = '🟡'
            
            message = f"{color} {emoji} Price Alert - {token_symbol}\n\n"
            message += f"🏛️ DAO: {dao_name}\n"
            
            # Получаем блокчейн из metadata
            metadata = alert_data.get('metadata', {})
            if isinstance(metadata, dict):
                blockchain = metadata.get('blockchain', '')
                if blockchain:
                    message += f"⛓️ Chain: {blockchain}\n"
            
            # Время в московской зоне
            timestamp = alert_data.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, datetime):
                    pass
                
                # Проверяем есть ли московское время в metadata
                moscow_time_str = metadata.get('moscow_time') if isinstance(metadata, dict) else None
                if moscow_time_str:
                    message += f"⏰ Time: {moscow_time_str} UTC+3\n"
                else:
                    # Конвертируем в московское время
                    moscow_tz = timezone(timedelta(hours=3))
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    moscow_time = timestamp.astimezone(moscow_tz)
                    message += f"⏰ Time: {moscow_time.strftime('%Y-%m-%d %H:%M:%S')} UTC+3\n"
            
            # Описание (здесь уже содержится информация о ценах)
            description = alert_data.get('message', '')
            if description:
                message += f"\n📝 Details: {description}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting price alert: {e}")
            return f"⚠️ Price alert formatting error: {alert_data.get('title', 'Unknown alert')}"
    
    def format_generic_alert(self, alert_data: Dict[str, Any]) -> str:
        """Форматирует общий алерт для Telegram"""
        try:
            alert_type = alert_data.get('alert_type', 'general')
            severity = alert_data.get('severity', 'medium')
            title = alert_data.get('title', 'Alert')
            message_text = alert_data.get('message', '')
            dao_name = alert_data.get('dao_name', '')
            
            # Эмодзи в зависимости от критичности
            severity_emoji = {
                'low': '🟢',
                'medium': '🟡', 
                'high': '🔴',
                'critical': '🚨'
            }.get(severity, '⚠️')
            
            message = f"{severity_emoji} **{title}**\n\n"
            
            if dao_name:
                message += f"🏛️ **DAO:** {dao_name}\n"
            
            if message_text:
                message += f"📝 **Message:** {message_text}\n"
            
            # Время
            timestamp = alert_data.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, datetime):
                    pass
                message += f"⏰ **Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting generic alert: {e}")
            return f"⚠️ Alert: {alert_data.get('title', 'Unknown alert')}"
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Отправляет алерт в Telegram"""
        if not self.enabled:
            logger.debug("Telegram notifications disabled, skipping alert")
            return False
        
        try:
            # Определяем тип алерта и форматируем сообщение
            alert_type = alert_data.get('alert_type', 'general')
            
            if alert_type in ['large_transaction', 'treasury_transaction']:
                message = self.format_transaction_alert(alert_data)
            elif alert_type in ['price_drop', 'price_spike', 'price_change']:
                message = self.format_price_alert(alert_data)
            else:
                message = self.format_generic_alert(alert_data)
            
            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Telegram alert sent: {alert_data.get('title', 'Unknown')}")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Отправляет ежедневную сводку"""
        if not self.enabled:
            return False
        
        try:
            # Форматируем ежедневную сводку
            date = summary_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            total_transactions = summary_data.get('total_transactions', 0)
            total_volume_usd = summary_data.get('total_volume_usd', 0)
            active_daos = summary_data.get('active_daos', [])
            top_transactions = summary_data.get('top_transactions', [])
            
            message = f"📊 **Daily DAO Treasury Summary - {date}**\n\n"
            message += f"📈 **Total Transactions:** {total_transactions}\n"
            message += f"💰 **Total Volume:** ${total_volume_usd:,.2f}\n"
            message += f"🏛️ **Active DAOs:** {len(active_daos)}\n"
            
            if active_daos:
                message += f"\n🎯 **Most Active DAOs:**\n"
                for dao in active_daos[:5]:  # Показываем топ 5
                    dao_name = dao.get('dao_name', 'Unknown')
                    dao_volume = dao.get('volume_usd', 0)
                    dao_tx_count = dao.get('transaction_count', 0)
                    message += f"  • {dao_name}: {dao_tx_count} tx, ${dao_volume:,.2f}\n"
            
            if top_transactions:
                message += f"\n🔝 **Largest Transactions:**\n"
                for i, tx in enumerate(top_transactions[:3], 1):  # Топ 3
                    dao_name = tx.get('dao_name', 'Unknown')
                    amount_usd = tx.get('amount_usd', 0)
                    token_symbol = tx.get('token_symbol', 'TOKEN')
                    message += f"  {i}. {dao_name}: ${amount_usd:,.2f} ({token_symbol})\n"
            
            message += f"\n🤖 *Generated by DAO Treasury Monitor*"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Daily summary sent to Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False
    
    async def send_test_message(self) -> bool:
        """Отправляет тестовое сообщение"""
        if not self.enabled:
            logger.warning("Telegram notifications not enabled")
            return False
        
        try:
            test_message = (
                "🤖 **DAO Treasury Monitor - Test Message**\n\n"
                f"✅ Telegram integration is working!\n"
                f"⏰ Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"You will receive alerts for:\n"
                f"• 📤 Large treasury transactions (>$10K)\n"
                f"• 📉 Significant price drops\n"
                f"• 📈 Major price spikes\n"
                f"• 📊 Daily activity summaries\n\n"
                f"🔧 Monitoring is now active!"
            )
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=test_message,
                parse_mode='Markdown'
            )
            
            logger.info("Test message sent to Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Error sending test message: {e}")
            return False

    async def send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """Отправляет произвольное сообщение в Telegram"""
        if not self.enabled:
            logger.warning("Telegram notifications not enabled")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
            
            logger.info("Message sent to Telegram successfully")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False

# Фабричная функция для создания уведомителя
def create_telegram_notifier(bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> TelegramNotifier:
    """Создает экземпляр Telegram уведомителя"""
    return TelegramNotifier(bot_token, chat_id)

# Асинхронная функция для быстрой отправки алерта
async def send_telegram_alert(alert_data: Dict[str, Any], 
                             bot_token: Optional[str] = None, 
                             chat_id: Optional[str] = None) -> bool:
    """Быстрая отправка алерта в Telegram"""
    notifier = create_telegram_notifier(bot_token, chat_id)
    if notifier.enabled:
        return await notifier.send_alert(alert_data)
    return False 