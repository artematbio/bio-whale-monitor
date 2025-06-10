#!/usr/bin/env python3
"""
Pool Monitor для DAO Treasury Monitor
Простой мониторинг активности в пулах ликвидности DAO:
- Крупные продажи DAO/BIO токенов > $10K
- Суммарные продажи DAO/BIO за день > $10K  
- Add/remove liquidity > $10K
"""

import asyncio
import logging
import time
import httpx
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from dataclasses import dataclass

from config.dao_config import ALL_DAOS, SOLANA_DAOS, ETHEREUM_DAOS, get_all_pool_addresses, BIO_TOKEN_SOLANA, BIO_TOKEN_ETHEREUM
from database.database import DAOTreasuryDatabase
from utils.price_utils import get_multiple_token_prices

logger = logging.getLogger(__name__)

@dataclass
class PoolActivityInfo:
    """Информация об активности в пуле"""
    tx_hash: str
    timestamp: datetime
    dao_name: str
    blockchain: str
    pool_address: str
    activity_type: str  # 'swap_sell', 'swap_buy', 'add_liquidity', 'remove_liquidity'
    token0_address: Optional[str] = None
    token1_address: Optional[str] = None
    token0_symbol: Optional[str] = None
    token1_symbol: Optional[str] = None
    token0_amount: Decimal = Decimal('0')
    token1_amount: Decimal = Decimal('0')
    total_usd_value: Decimal = Decimal('0')
    dao_token_sold: bool = False  # Флаг продажи DAO токена
    bio_token_sold: bool = False  # Флаг продажи BIO токена
    metadata: Dict[str, Any] = None

class PoolMonitor:
    """Простой мониторинг активности в пулах ликвидности DAO"""
    
    def __init__(self, database: DAOTreasuryDatabase):
        self.database = database
        self.http_client = None
        
        # Настройки мониторинга
        self.check_interval = 60  # Проверка каждую минуту
        self.alert_threshold = Decimal("10000")  # $10,000 порог алерта
        self.daily_sale_threshold = Decimal("10000")  # $10,000 порог за день
        
        # Кэш для оптимизации
        self.token_prices_cache = {}
        self.price_cache_ttl = 300  # 5 минут
        self.last_price_update = 0
        self.daily_sales_cache = {}  # Кэш продаж за день
        
        # Пулы для мониторинга
        self.pool_addresses = get_all_pool_addresses()
        self.solana_pools = self._get_solana_pools()
        self.ethereum_pools = self._get_ethereum_pools()
        
        # API настройки
        self.helius_api_key = self._get_helius_key()
        self.helius_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"
        self.bitquery_endpoint = "https://streaming.bitquery.io/eap"
        self.bitquery_api_key = self._get_bitquery_key()
        
        # Списки DAO и BIO токенов для отслеживания
        self.dao_token_addresses = {dao.token_address: dao.token_symbol for dao in ALL_DAOS}
        self.bio_token_addresses = {BIO_TOKEN_SOLANA: 'BIO', BIO_TOKEN_ETHEREUM: 'BIO'}
        
        logger.info(f"Initialized Pool Monitor for {len(self.pool_addresses)} pools")
        logger.info(f"Monitoring {len(self.dao_token_addresses)} DAO tokens and {len(self.bio_token_addresses)} BIO tokens")
        logger.info(f"Solana pools: {len(self.solana_pools)}, Ethereum pools: {len(self.ethereum_pools)}")
    
    def _get_helius_key(self) -> str:
        """Получение Helius API ключа из переменных окружения"""
        import os
        return os.getenv('HELIUS_API_KEY', '')
    
    def _get_bitquery_key(self) -> str:
        """Получение BitQuery API ключа"""
        import os
        return os.getenv('BITQUERY_API_KEY', '')
    
    def _get_solana_pools(self) -> List[Dict[str, Any]]:
        """Получение списка Solana пулов для мониторинга"""
        pools = []
        for dao in SOLANA_DAOS:
            if dao.pools:
                for pool_addr in dao.pools:
                    pools.append({
                        'address': pool_addr,
                        'dao_name': dao.name,
                        'dao_token_symbol': dao.token_symbol,
                        'dao_token_address': dao.token_address
                    })
        return pools
    
    def _get_ethereum_pools(self) -> List[Dict[str, Any]]:
        """Получение списка Ethereum пулов для мониторинга"""
        pools = []
        for dao in ETHEREUM_DAOS:
            pool_addresses = []
            if dao.eth_pool_address:
                pool_addresses.append(dao.eth_pool_address)
            if dao.bio_pool_address:
                pool_addresses.append(dao.bio_pool_address)
            
            for pool_addr in pool_addresses:
                pools.append({
                    'address': pool_addr,
                    'dao_name': dao.name,
                    'dao_token_symbol': dao.token_symbol,
                    'dao_token_address': dao.token_address
                })
        return pools
    
    async def start_session(self):
        """Инициализация HTTP клиента"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def close_session(self):
        """Закрытие HTTP клиента"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def run_pool_monitoring_cycle(self):
        """Основной цикл мониторинга пулов"""
        try:
            await self.start_session()
            
            start_time = time.time()
            logger.info("🏊 Starting pool monitoring cycle")
            
            # Обновляем цены токенов
            await self.update_token_prices()
            
            # Мониторинг Solana пулов
            solana_activities = await self.monitor_solana_pools()
            
            # Мониторинг Ethereum пулов
            ethereum_activities = await self.monitor_ethereum_pools()
            
            # Объединяем активности
            all_activities = solana_activities + ethereum_activities
            
            # Фильтруем только значимые активности
            significant_activities = self.filter_significant_activities(all_activities)
            
            # Проверяем дневные лимиты продаж
            daily_alerts = await self.check_daily_sales_limits()
            
            # Сохраняем активности в базу данных
            if significant_activities:
                await self.save_pool_activities(significant_activities)
                logger.info(f"💾 Saved {len(significant_activities)} significant pool activities")
            
            # Генерируем алерты
            alerts_generated = await self.generate_alerts(significant_activities, daily_alerts)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ Pool monitoring cycle completed in {processing_time:.2f}s")
            logger.info(f"📊 Found {len(all_activities)} activities, {len(significant_activities)} significant, {alerts_generated} alerts")
            
        except Exception as e:
            logger.error(f"❌ Error in pool monitoring cycle: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            await self.close_session()
    
    def filter_significant_activities(self, activities: List[PoolActivityInfo]) -> List[PoolActivityInfo]:
        """Фильтрация только значимых активностей"""
        significant = []
        
        for activity in activities:
            # Критерии значимости:
            # 1. Транзакция > $10K
            # 2. Продажа DAO или BIO токена любого размера
            # 3. Add/Remove liquidity > $10K
            
            is_significant = False
            
            # Крупная транзакция
            if activity.total_usd_value >= self.alert_threshold:
                is_significant = True
                logger.info(f"🚨 Large transaction: ${activity.total_usd_value} in {activity.dao_name} pool")
            
            # Продажа DAO или BIO токена
            if activity.dao_token_sold or activity.bio_token_sold:
                is_significant = True
                token_type = "DAO" if activity.dao_token_sold else "BIO"
                logger.info(f"📉 {token_type} token sale: ${activity.total_usd_value} in {activity.dao_name} pool")
            
            # Add/Remove liquidity
            if activity.activity_type in ['add_liquidity', 'remove_liquidity'] and activity.total_usd_value >= self.alert_threshold:
                is_significant = True
                logger.info(f"💧 Large liquidity operation: {activity.activity_type} ${activity.total_usd_value}")
            
            if is_significant:
                significant.append(activity)
                # Обновляем дневную статистику продаж
                self.update_daily_sales_cache(activity)
        
        return significant
    
    def update_daily_sales_cache(self, activity: PoolActivityInfo):
        """Обновление кэша дневных продаж"""
        today = datetime.now().date()
        
        if today not in self.daily_sales_cache:
            self.daily_sales_cache[today] = {
                'dao_sales': Decimal('0'),
                'bio_sales': Decimal('0'),
                'total_sales': Decimal('0')
            }
        
        if activity.dao_token_sold:
            self.daily_sales_cache[today]['dao_sales'] += activity.total_usd_value
        
        if activity.bio_token_sold:
            self.daily_sales_cache[today]['bio_sales'] += activity.total_usd_value
        
        self.daily_sales_cache[today]['total_sales'] += activity.total_usd_value
    
    async def check_daily_sales_limits(self) -> List[Dict[str, Any]]:
        """Проверка лимитов дневных продаж"""
        today = datetime.now().date()
        alerts = []
        
        if today in self.daily_sales_cache:
            daily_data = self.daily_sales_cache[today]
            
            # Проверяем лимиты
            if daily_data['dao_sales'] >= self.daily_sale_threshold:
                alerts.append({
                    'type': 'daily_dao_sales',
                    'amount': daily_data['dao_sales'],
                    'threshold': self.daily_sale_threshold,
                    'date': today
                })
            
            if daily_data['bio_sales'] >= self.daily_sale_threshold:
                alerts.append({
                    'type': 'daily_bio_sales',
                    'amount': daily_data['bio_sales'],
                    'threshold': self.daily_sale_threshold,
                    'date': today
                })
        
        return alerts
    
    async def update_token_prices(self):
        """Обновление кэша цен токенов"""
        current_time = time.time()
        
        if current_time - self.last_price_update < self.price_cache_ttl:
            return
        
        try:
            # Получаем цены всех DAO и BIO токенов
            all_tokens = list(self.dao_token_addresses.keys()) + list(self.bio_token_addresses.keys())
            
            # Группируем по блокчейнам
            ethereum_tokens = [token for token in all_tokens if token == BIO_TOKEN_ETHEREUM or any(dao.token_address == token and dao.blockchain == 'ethereum' for dao in ALL_DAOS)]
            solana_tokens = [token for token in all_tokens if token not in ethereum_tokens]
            
            # Получаем цены
            if ethereum_tokens:
                eth_prices = await get_multiple_token_prices(ethereum_tokens, 'ethereum', self.http_client)
                self.token_prices_cache.update(eth_prices)
            
            if solana_tokens:
                sol_prices = await get_multiple_token_prices(solana_tokens, 'solana', self.http_client)
                self.token_prices_cache.update(sol_prices)
            
            self.last_price_update = current_time
            logger.info(f"💰 Updated prices for {len(self.token_prices_cache)} tokens")
            
        except Exception as e:
            logger.error(f"Error updating token prices: {e}")
    
    async def monitor_solana_pools(self) -> List[PoolActivityInfo]:
        """Мониторинг Solana пулов через BitQuery"""
        activities = []
        
        try:
            logger.info(f"🔍 Monitoring {len(self.solana_pools)} Solana pools")
            
            for pool_info in self.solana_pools:
                pool_activities = await self.fetch_solana_pool_trades(
                    pool_info['address'],
                    pool_info['dao_name'],
                    pool_info['dao_token_address']
                )
                activities.extend(pool_activities)
            
            logger.info(f"📈 Found {len(activities)} Solana pool activities")
            
        except Exception as e:
            logger.error(f"Error monitoring Solana pools: {e}")
        
        return activities
    
    async def monitor_ethereum_pools(self) -> List[PoolActivityInfo]:
        """Мониторинг Ethereum пулов"""
        activities = []
        
        try:
            logger.info(f"🔍 Monitoring {len(self.ethereum_pools)} Ethereum pools")
            
            # TODO: Реализовать мониторинг Ethereum пулов через Web3
            # Пока оставляем заглушку
            
        except Exception as e:
            logger.error(f"Error monitoring Ethereum pools: {e}")
        
        return activities
    
    async def fetch_solana_pool_trades(self, pool_address: str, dao_name: str, dao_token_address: str) -> List[PoolActivityInfo]:
        """Получение торгов Solana пула за последний час"""
        activities = []
        
        try:
            # Время начала (последний час)
            time_since = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Простой GraphQL запрос для получения торгов
            query = """
            query poolTrades($poolAddress: String, $since: DateTime!) {
              Solana(network: solana, dataset: archive) {
                DEXTrades(
                  where: {
                    Trade: {Dex: {PoolAddress: {is: $poolAddress}}},
                    Block: {Time: {since: $since}}
                  }
                  orderBy: {descending: Block_Time}
                  limit: {count: 50}
                ) {
                  Block {
                    Time
                  }
                  Transaction {
                    Signature
                  }
                  Trade {
                    Buy {
                      Amount
                      Currency {
                        MintAddress
                        Symbol
                      }
                      AmountInUSD
                    }
                    Sell {
                      Amount
                      Currency {
                        MintAddress
                        Symbol
                      }
                      AmountInUSD
                    }
                  }
                }
              }
            }
            """
            
            if not self.bitquery_api_key:
                logger.debug(f"BitQuery API key not configured, skipping pool {pool_address}")
                return activities
            
            variables = {"poolAddress": pool_address, "since": time_since}
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.bitquery_api_key}"
            }
            
            response = await self.http_client.post(
                self.bitquery_endpoint, 
                json={"query": query, "variables": variables}, 
                headers=headers
            )
            
            if response.status_code != 200:
                logger.debug(f"BitQuery API error {response.status_code} for pool {pool_address}")
                return activities
            
            data = response.json()
            trades = data.get("data", {}).get("Solana", {}).get("DEXTrades", [])
            
            for trade in trades:
                activity = self.parse_solana_trade(trade, pool_address, dao_name, dao_token_address)
                if activity:
                    activities.append(activity)
            
        except Exception as e:
            logger.error(f"Error fetching Solana pool trades for {pool_address}: {e}")
        
        return activities
    
    def parse_solana_trade(self, trade_data: Dict[str, Any], pool_address: str, dao_name: str, dao_token_address: str) -> Optional[PoolActivityInfo]:
        """Парсинг торга Solana"""
        try:
            block_data = trade_data.get("Block", {})
            transaction_data = trade_data.get("Transaction", {})
            trade_info = trade_data.get("Trade", {})
            
            tx_hash = transaction_data.get("Signature", "")
            timestamp_str = block_data.get("Time")
            
            if not tx_hash or not timestamp_str:
                return None
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            buy_data = trade_info.get("Buy", {})
            sell_data = trade_info.get("Sell", {})
            
            buy_currency = buy_data.get("Currency", {})
            sell_currency = sell_data.get("Currency", {})
            
            buy_token_address = buy_currency.get("MintAddress", "")
            sell_token_address = sell_currency.get("MintAddress", "")
            
            buy_symbol = buy_currency.get("Symbol", "Unknown")
            sell_symbol = sell_currency.get("Symbol", "Unknown")
            
            buy_amount = Decimal(str(buy_data.get("Amount", 0)))
            sell_amount = Decimal(str(sell_data.get("Amount", 0)))
            
            buy_usd = Decimal(str(buy_data.get("AmountInUSD", 0)))
            sell_usd = Decimal(str(sell_data.get("AmountInUSD", 0)))
            
            total_usd_value = max(buy_usd, sell_usd)
            
            # Определяем, продается ли DAO или BIO токен
            dao_token_sold = (sell_token_address == dao_token_address or 
                            sell_token_address in self.dao_token_addresses)
            bio_token_sold = sell_token_address in self.bio_token_addresses
            
            # Определяем тип активности
            if dao_token_sold or bio_token_sold:
                activity_type = "swap_sell"
            else:
                activity_type = "swap_buy"
            
            activity = PoolActivityInfo(
                tx_hash=tx_hash,
                timestamp=timestamp,
                dao_name=dao_name,
                blockchain="solana",
                pool_address=pool_address,
                activity_type=activity_type,
                token0_address=buy_token_address,
                token1_address=sell_token_address,
                token0_symbol=buy_symbol,
                token1_symbol=sell_symbol,
                token0_amount=buy_amount,
                token1_amount=sell_amount,
                total_usd_value=total_usd_value,
                dao_token_sold=dao_token_sold,
                bio_token_sold=bio_token_sold,
                metadata={
                    "buy_usd": str(buy_usd),
                    "sell_usd": str(sell_usd)
                }
            )
            
            return activity
            
        except Exception as e:
            logger.error(f"Error parsing Solana trade: {e}")
            return None
    
    async def save_pool_activities(self, activities: List[PoolActivityInfo]):
        """Сохранение активностей пулов в базу данных"""
        for activity in activities:
            try:
                activity_data = {
                    'tx_hash': activity.tx_hash,
                    'timestamp': activity.timestamp,
                    'dao_name': activity.dao_name,
                    'blockchain': activity.blockchain,
                    'pool_address': activity.pool_address,
                    'activity_type': activity.activity_type,
                    'token0_address': activity.token0_address,
                    'token1_address': activity.token1_address,
                    'token0_symbol': activity.token0_symbol,
                    'token1_symbol': activity.token1_symbol,
                    'token0_amount': activity.token0_amount,
                    'token1_amount': activity.token1_amount,
                    'total_usd_value': activity.total_usd_value,
                    'alert_triggered': activity.total_usd_value >= self.alert_threshold or activity.dao_token_sold or activity.bio_token_sold,
                    'metadata': {
                        **activity.metadata,
                        'dao_token_sold': activity.dao_token_sold,
                        'bio_token_sold': activity.bio_token_sold
                    }
                }
                
                success = self.database.save_pool_activity(activity_data)
                if success:
                    logger.debug(f"💾 Saved pool activity: {activity.dao_name} - ${activity.total_usd_value}")
                
            except Exception as e:
                logger.error(f"Error saving pool activity: {e}")
    
    async def generate_alerts(self, activities: List[PoolActivityInfo], daily_alerts: List[Dict[str, Any]]) -> int:
        """Генерация алертов"""
        alerts_count = 0
        
        # Алерты для отдельных транзакций
        for activity in activities:
            if (activity.total_usd_value >= self.alert_threshold or 
                activity.dao_token_sold or activity.bio_token_sold):
                
                alert_message = self.format_activity_alert(activity)
                logger.warning(f"🚨 POOL ALERT: {alert_message}")
                alerts_count += 1
        
        # Алерты для дневных лимитов
        for daily_alert in daily_alerts:
            alert_message = self.format_daily_alert(daily_alert)
            logger.warning(f"🚨 DAILY LIMIT ALERT: {alert_message}")
            alerts_count += 1
        
        return alerts_count
    
    def format_activity_alert(self, activity: PoolActivityInfo) -> str:
        """Форматирование алерта для активности"""
        alert_type = ""
        if activity.dao_token_sold:
            alert_type = "DAO Token Sale"
        elif activity.bio_token_sold:
            alert_type = "BIO Token Sale"
        elif activity.total_usd_value >= self.alert_threshold:
            alert_type = "Large Transaction"
        
        return (
            f"{alert_type} detected!\n"
            f"DAO: {activity.dao_name}\n"
            f"Pool: {activity.pool_address}\n"
            f"Type: {activity.activity_type}\n"
            f"Tokens: {activity.token0_symbol} → {activity.token1_symbol}\n"
            f"Value: ${activity.total_usd_value:,.2f}\n"
            f"Tx: {activity.tx_hash}\n"
            f"Time: {activity.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def format_daily_alert(self, daily_alert: Dict[str, Any]) -> str:
        """Форматирование алерта для дневных лимитов"""
        alert_type = daily_alert['type']
        amount = daily_alert['amount']
        threshold = daily_alert['threshold']
        date = daily_alert['date']
        
        if alert_type == 'daily_dao_sales':
            token_type = "DAO tokens"
        else:
            token_type = "BIO tokens"
        
        return (
            f"Daily {token_type} sales limit exceeded!\n"
            f"Date: {date}\n"
            f"Total sales: ${amount:,.2f}\n"
            f"Threshold: ${threshold:,.2f}\n"
            f"Exceeded by: ${amount - threshold:,.2f}"
        ) 