#!/usr/bin/env python3
"""
Price Tracker для DAO Treasury Monitor
Отслеживает изменения цен токенов и создает алерты при значительных изменениях
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import httpx

from config.dao_config import ALL_DAOS, BIO_TOKEN_ETHEREUM, BIO_TOKEN_SOLANA
from database.database import DAOTreasuryDatabase
from utils.price_utils import get_multiple_token_prices, get_token_price_coingecko

logger = logging.getLogger(__name__)

class PriceTracker:
    """Класс для отслеживания изменений цен токенов"""
    
    def __init__(self, database: DAOTreasuryDatabase):
        self.database = database
        self.http_client = None
        
        # Настройки трекинга
        self.price_check_interval = 300  # 5 минут между проверками
        self.price_drop_threshold = 5.0  # 5% падение для алерта
        self.price_spike_threshold = 15.0  # 15% рост для алерта
        self.comparison_periods = [1, 4, 24]  # 1, 4 и 24 часа для сравнения
        
        # Токены для мониторинга
        self.tokens_to_track = self._get_tokens_list()
        
        logger.info(f"Initialized Price Tracker for {len(self.tokens_to_track)} tokens")
    
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
                            'timestamp': datetime.now()
                        }
            
            if solana_tokens:
                sol_addresses = [t['address'] for t in solana_tokens]
                sol_prices = await get_multiple_token_prices(sol_addresses, 'solana', self.http_client)
                
                for token in solana_tokens:
                    if token['address'] in sol_prices:
                        prices[token['address']] = {
                            'price_usd': sol_prices[token['address']],
                            'token_info': token,
                            'timestamp': datetime.now()
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
    
    def check_price_alerts(self, token_address: str, token_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Проверка ценовых алертов для токена"""
        alerts = []
        
        try:
            # Проверяем изменения за разные периоды
            for hours in self.comparison_periods:
                change_percentage = self.database.get_price_change_percentage(token_address, hours)
                
                if change_percentage is None:
                    continue
                
                # Проверяем падение цены
                if change_percentage <= -self.price_drop_threshold:
                    alert = {
                        'alert_type': 'price_drop',
                        'dao_name': token_info['dao_name'],
                        'severity': 'high' if change_percentage <= -10 else 'medium',
                        'title': f'Price Drop Alert - {token_info["symbol"]}',
                        'message': f'{token_info["symbol"]} price dropped {abs(change_percentage):.2f}% in {hours}h',
                        'token_address': token_address,
                        'token_symbol': token_info['symbol'],
                        'price_change': change_percentage,
                        'time_period': f'{hours}h',
                        'timestamp': datetime.now(),
                        'metadata': {
                            'blockchain': token_info['blockchain'],
                            'change_percentage': change_percentage,
                            'period_hours': hours,
                            'threshold_triggered': 'price_drop'
                        }
                    }
                    alerts.append(alert)
                    
                # Проверяем резкий рост цены (может быть полезно)
                elif change_percentage >= self.price_spike_threshold:
                    alert = {
                        'alert_type': 'price_spike',
                        'dao_name': token_info['dao_name'],
                        'severity': 'low',
                        'title': f'Price Spike Alert - {token_info["symbol"]}',
                        'message': f'{token_info["symbol"]} price increased {change_percentage:.2f}% in {hours}h',
                        'token_address': token_address,
                        'token_symbol': token_info['symbol'],
                        'price_change': change_percentage,
                        'time_period': f'{hours}h',
                        'timestamp': datetime.now(),
                        'metadata': {
                            'blockchain': token_info['blockchain'],
                            'change_percentage': change_percentage,
                            'period_hours': hours,
                            'threshold_triggered': 'price_spike'
                        }
                    }
                    alerts.append(alert)
            
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
                alerts = self.check_price_alerts(token_address, token_info)
                
                # Сохраняем алерты в базу данных
                for alert in alerts:
                    success = self.database.save_alert(alert)
                    if success:
                        total_alerts += 1
                        logger.warning(f"PRICE ALERT: {alert['message']}")
                
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