#!/usr/bin/env python3
"""
Price Tracker для DAO Treasury Monitor
Отслеживает изменения цен токенов и создает алерты при значительных изменениях
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from decimal import Decimal
import httpx

from config.dao_config import ALL_DAOS, BIO_TOKEN_ETHEREUM, BIO_TOKEN_SOLANA
from database.database import DAOTreasuryDatabase
from utils.price_utils import get_multiple_token_prices, get_token_price_coingecko

logger = logging.getLogger(__name__)

# Московское время (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

class PriceTracker:
    """Класс для отслеживания изменений цен токенов"""
    
    def __init__(self, database: DAOTreasuryDatabase, notification_system=None):
        self.database = database
        self.notification_system = notification_system
        self.http_client = None
        
        # Настройки трекинга
        self.price_check_interval = 300  # 5 минут между проверками
        self.minimum_alert_threshold = 5.0  # Минимальное изменение для алерта (5%)
        
        # Пороговые уровни для уведомлений (каждые 5% падения от последней цены алерта)
        self.alert_thresholds = [-5, -10, -15, -20, -25, -30, -40, -50, -60, -70, -80, -90]
        
        # Кэш последних цен для каждого токена при которых были отправлены алерты
        # Структура: {token_address: {threshold: {'price': float, 'timestamp': datetime}}}
        self.last_alert_prices = {}
        
        # Минимальный интервал между алертами одного типа (30 минут)
        self.alert_cooldown = 1800  # секунды
        
        # Токены для мониторинга
        self.tokens_to_track = self._get_tokens_list()
        
        logger.info(f"Initialized Price Tracker for {len(self.tokens_to_track)} tokens")
        logger.info(f"Alert thresholds: {self.alert_thresholds}%")
    
    def _get_tokens_list(self) -> List[Dict[str, str]]:
        """Получение списка токенов для отслеживания"""
        tokens = []
        
        # Добавляем все токены DAO
        for dao in ALL_DAOS:
            tokens.append({
                'address': dao.token_address,
                'symbol': dao.token_symbol,
                'blockchain': dao.blockchain,
                'dao_name': dao.name
            })
        
        # Добавляем BIO токены если их еще нет
        bio_ethereum = {
            'address': BIO_TOKEN_ETHEREUM,
            'symbol': 'BIO',
            'blockchain': 'ethereum',
            'dao_name': 'BIO Protocol'
        }
        
        bio_solana = {
            'address': BIO_TOKEN_SOLANA,
            'symbol': 'BIO',
            'blockchain': 'solana',
            'dao_name': 'BIO Protocol'
        }
        
        # Проверяем, нет ли уже BIO токенов в списке
        existing_addresses = [token['address'] for token in tokens]
        if BIO_TOKEN_ETHEREUM not in existing_addresses:
            tokens.append(bio_ethereum)
        if BIO_TOKEN_SOLANA not in existing_addresses:
            tokens.append(bio_solana)
        
        return tokens
    
    def _get_blockchain_display_name(self, blockchain: str) -> str:
        """Получает красивое название блокчейна"""
        blockchain_names = {
            'ethereum': 'Ethereum',
            'solana': 'Solana',
            'polygon': 'Polygon',
            'arbitrum': 'Arbitrum',
            'optimism': 'Optimism'
        }
        return blockchain_names.get(blockchain.lower(), blockchain.title())
    
    def _should_send_alert(self, token_address: str, current_price: float, threshold: int) -> tuple[bool, float]:
        """
        Проверяет, нужно ли отправлять алерт для данного порога
        Возвращает (should_send, reference_price)
        """
        now = datetime.now()
        
        # Инициализируем кэш для токена если нужно
        if token_address not in self.last_alert_prices:
            self.last_alert_prices[token_address] = {}
        
        # Проверяем есть ли запись для этого порога
        if threshold not in self.last_alert_prices[token_address]:
            # Первый алерт для этого порога - используем текущую цену как базовую
            # Но нужно найти максимальную цену из всех более высоких порогов
            reference_price = current_price
            
            # Ищем цену для менее негативного порога (например, для -10% берем цену -5%)
            for higher_threshold in sorted([t for t in self.alert_thresholds if t > threshold], reverse=True):
                if higher_threshold in self.last_alert_prices[token_address]:
                    reference_price = self.last_alert_prices[token_address][higher_threshold]['price']
                    break
            
            # Если это первый порог (-5%), берем максимальную цену за последние 24 часа
            if threshold == -5:
                try:
                    recent_prices = self.database.get_token_price_history(token_address, 24)
                    if recent_prices:
                        max_price = max(float(p.get('price_usd', 0)) for p in recent_prices)
                        if max_price > current_price:
                            reference_price = max_price
                except Exception as e:
                    logger.debug(f"Could not get price history for {token_address}: {e}")
            
            return True, reference_price
        
        # Проверяем время последнего алерта (кулдаун)
        last_alert_info = self.last_alert_prices[token_address][threshold]
        time_since_last = (now - last_alert_info['timestamp']).total_seconds()
        
        if time_since_last < self.alert_cooldown:
            return False, last_alert_info['price']
        
        # Проверяем достиг ли порог относительно последней цены алерта
        reference_price = last_alert_info['price']
        price_change_percent = ((current_price - reference_price) / reference_price * 100)
        
        # Алерт нужен если цена упала еще на 5% от последней цены алерта
        return price_change_percent <= -5, reference_price
    
    def _mark_alert_sent(self, token_address: str, threshold: int, price: float):
        """Отмечает что алерт был отправлен"""
        if token_address not in self.last_alert_prices:
            self.last_alert_prices[token_address] = {}
        
        self.last_alert_prices[token_address][threshold] = {
            'price': price,
            'timestamp': datetime.now()
        }
    
    def _get_threshold_for_current_drop(self, current_price: float, reference_price: float) -> Optional[int]:
        """Определяет пороговый уровень для текущего падения цены"""
        if reference_price <= 0:
            return None
        
        change_percentage = ((current_price - reference_price) / reference_price * 100)
        
        # Находим подходящий порог
        for threshold in sorted(self.alert_thresholds):
            if change_percentage <= threshold:
                return threshold
        
        return None
    
    async def start_session(self):
        """Инициализация HTTP клиента"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close_session(self):
        """Закрытие HTTP клиента"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def fetch_current_prices(self) -> Dict[str, Dict[str, Any]]:
        """Получение текущих цен всех токенов"""
        prices = {}
        
        try:
            # Группируем токены по блокчейнам
            ethereum_tokens = [t for t in self.tokens_to_track if t['blockchain'] == 'ethereum']
            solana_tokens = [t for t in self.tokens_to_track if t['blockchain'] == 'solana']
            
            # Получаем цены пакетами
            if ethereum_tokens:
                eth_addresses = [t['address'] for t in ethereum_tokens]
                eth_prices = await get_multiple_token_prices(eth_addresses, 'ethereum', self.http_client)
                
                for token in ethereum_tokens:
                    if token['address'] in eth_prices:
                        prices[token['address']] = {
                            'price_usd': eth_prices[token['address']],
                            'token_info': token,
                            'timestamp': datetime.now(MOSCOW_TZ)
                        }
            
            if solana_tokens:
                sol_addresses = [t['address'] for t in solana_tokens]
                sol_prices = await get_multiple_token_prices(sol_addresses, 'solana', self.http_client)
                
                for token in solana_tokens:
                    if token['address'] in sol_prices:
                        prices[token['address']] = {
                            'price_usd': sol_prices[token['address']],
                            'token_info': token,
                            'timestamp': datetime.now(MOSCOW_TZ)
                        }
            
            logger.info(f"Fetched prices for {len(prices)}/{len(self.tokens_to_track)} tokens")
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching current prices: {e}")
            return {}
    
    async def save_price_data(self, prices: Dict[str, Dict[str, Any]]):
        """Сохранение данных о ценах в базу данных"""
        for token_address, price_data in prices.items():
            try:
                token_info = price_data['token_info']
                
                price_record = {
                    'token_address': token_address,
                    'token_symbol': token_info['symbol'],
                    'blockchain': token_info['blockchain'],
                    'price_usd': price_data['price_usd'],
                    'timestamp': price_data['timestamp'],
                    'metadata': {
                        'dao_name': token_info['dao_name'],
                        'tracker_cycle': True
                    }
                }
                
                success = self.database.save_token_price(price_record)
                if success:
                    logger.debug(f"Saved price for {token_info['symbol']}: ${price_data['price_usd']}")
                
            except Exception as e:
                logger.error(f"Error saving price for {token_address}: {e}")
    
    def check_price_alerts(self, token_address: str, token_info: Dict[str, str], current_price: float) -> List[Dict[str, Any]]:
        """Проверка ценовых алертов для токена с новой логикой"""
        alerts = []
        
        try:
            # Проверяем каждый пороговый уровень
            for threshold in self.alert_thresholds:
                should_alert, reference_price = self._should_send_alert(token_address, current_price, threshold)
                
                if should_alert and reference_price > 0:
                    # Проверяем достигнут ли этот порог
                    actual_change = ((current_price - reference_price) / reference_price * 100)
                    
                    if actual_change <= threshold:
                        # Создаем сообщение с корректными ценами
                        blockchain_name = self._get_blockchain_display_name(token_info['blockchain'])
                        moscow_time = datetime.now(MOSCOW_TZ)
                        
                        message = (f'{token_info["symbol"]} price dropped {abs(actual_change):.2f}%\n'
                                 f'📉 ${reference_price:.6f} → ${current_price:.6f}')
                        
                        alert = {
                            'alert_type': 'price_drop',
                            'dao_name': token_info['dao_name'],
                            'severity': 'high' if actual_change <= -20 else 'medium',
                            'title': f'Price Drop Alert - {token_info["symbol"]}',
                            'message': message,
                            'token_address': token_address,
                            'token_symbol': token_info['symbol'],
                            'price_change': actual_change,
                            'timestamp': moscow_time,
                            'metadata': {
                                'blockchain': blockchain_name,
                                'change_percentage': actual_change,
                                'threshold_triggered': threshold,
                                'alert_type': 'threshold_drop',
                                'current_price': current_price,
                                'reference_price': reference_price,
                                'moscow_time': moscow_time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                        }
                        alerts.append(alert)
                        
                        # Отмечаем что алерт отправлен
                        self._mark_alert_sent(token_address, threshold, reference_price)
                        
                        logger.info(f"🚨 Price threshold alert: {token_info['symbol']} {threshold}% (${reference_price:.6f} → ${current_price:.6f})")
                        
                        # Берем только первый сработавший порог
                        break
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking price alerts for {token_address}: {e}")
            return []
    
    async def process_price_alerts(self, prices: Dict[str, Dict[str, Any]]):
        """Обработка ценовых алертов для всех токенов"""
        total_alerts = 0
        
        for token_address, price_data in prices.items():
            try:
                token_info = price_data['token_info']
                current_price = price_data['price_usd']
                
                alerts = self.check_price_alerts(token_address, token_info, current_price)
                
                # Сохраняем алерты в базу данных
                for alert in alerts:
                    success = self.database.save_alert(alert)
                    if success:
                        total_alerts += 1
                        logger.warning(f"PRICE ALERT: {alert['message']}")
                        
                        # Отправляем уведомления в Telegram через notification_system
                        if self.notification_system:
                            try:
                                await self.notification_system.send_price_alert(alert)
                            except Exception as e:
                                logger.error(f"Failed to send Telegram alert: {e}")
                
            except Exception as e:
                logger.error(f"Error processing alerts for {token_address}: {e}")
        
        if total_alerts > 0:
            logger.info(f"Generated {total_alerts} price alerts")
        
        return total_alerts
    
    async def run_price_tracking_cycle(self):
        """Один цикл отслеживания цен"""
        start_time = time.time()
        
        logger.info("Starting price tracking cycle")
        
        try:
            await self.start_session()
            
            # Получаем текущие цены
            current_prices = await self.fetch_current_prices()
            
            if current_prices:
                # Сохраняем цены в базу данных
                await self.save_price_data(current_prices)
                
                # Проверяем алерты
                alerts_count = await self.process_price_alerts(current_prices)
                
                logger.info(f"Price tracking completed: {len(current_prices)} prices saved, {alerts_count} alerts generated")
            else:
                logger.warning("No prices fetched in this cycle")
            
        except Exception as e:
            logger.error(f"Error in price tracking cycle: {e}")
        
        finally:
            await self.close_session()
        
        duration = time.time() - start_time
        logger.info(f"Price tracking cycle completed in {duration:.2f}s")
    
    async def start_price_tracking(self):
        """Запуск непрерывного отслеживания цен"""
        logger.info("Starting continuous price tracking")
        
        while True:
            try:
                await self.run_price_tracking_cycle()
                
                # Очистка старых записей раз в день
                if datetime.now().hour == 0 and datetime.now().minute < 10:
                    self.database.cleanup_old_prices(days=30)
                
                # Ожидание до следующего цикла
                logger.debug(f"Waiting {self.price_check_interval} seconds until next price check")
                await asyncio.sleep(self.price_check_interval)
                
            except KeyboardInterrupt:
                logger.info("Price tracking interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in price tracking loop: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке

if __name__ == "__main__":
    # Тестирование price tracker
    logging.basicConfig(level=logging.INFO)
    
    # Инициализируем базу данных
    database = DAOTreasuryDatabase()
    
    # Создаем price tracker
    tracker = PriceTracker(database)
    
    # Запуск отслеживания
    try:
        asyncio.run(tracker.start_price_tracking())
    except KeyboardInterrupt:
        logger.info("Price tracking stopped") 