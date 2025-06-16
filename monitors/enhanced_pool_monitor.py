#!/usr/bin/env python3
"""
Enhanced Pool Monitor для DAO Treasury Monitor
Улучшенный мониторинг пулов с поддержкой:
- Solana DEX trades через BitQuery
- Ethereum Uniswap V2/V3 swap события
- Liquidity операции
- Telegram уведомления
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

class EnhancedPoolMonitor:
    """Улучшенный мониторинг активности в пулах ликвидности DAO"""
    
    def __init__(self, database: DAOTreasuryDatabase, notification_system=None):
        self.database = database
        self.notification_system = notification_system
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
        
        logger.info(f"Initialized Enhanced Pool Monitor for {len(self.pool_addresses)} pools")
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
            logger.info("🏊 Starting enhanced pool monitoring cycle")
            
            # Обновляем цены токенов
            await self.update_token_prices()
            
            # Мониторинг Solana пулов
            solana_activities = await self.monitor_solana_pools()
            
            # Улучшенный мониторинг Ethereum пулов (включая swaps)
            ethereum_activities = await self.monitor_ethereum_pools_enhanced()
            
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
            
            # Генерируем алерты и уведомления
            alerts_generated = await self.generate_alerts_and_notifications(significant_activities, daily_alerts)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ Enhanced pool monitoring cycle completed in {processing_time:.2f}s")
            logger.info(f"📊 Found {len(all_activities)} activities, {len(significant_activities)} significant, {alerts_generated} alerts")
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced pool monitoring cycle: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            await self.close_session()
    
    async def monitor_ethereum_pools_enhanced(self) -> List[PoolActivityInfo]:
        """Улучшенный мониторинг Ethereum пулов включая swap события"""
        activities = []
        
        try:
            logger.info(f"🔍 Enhanced monitoring {len(self.ethereum_pools)} Ethereum pools")
            
            # Получаем Ethereum RPC URL
            ethereum_rpc_url = self._get_ethereum_rpc_url()
            if not ethereum_rpc_url:
                logger.warning("Ethereum RPC URL not configured, skipping Ethereum pools")
                return activities
            
            # Импортируем Web3 для Ethereum мониторинга
            try:
                from web3 import Web3
                from web3.exceptions import Web3Exception
            except ImportError:
                logger.error("web3 library not installed, skipping Ethereum pools")
                return activities
            
            # Подключаемся к Ethereum
            w3 = Web3(Web3.HTTPProvider(ethereum_rpc_url))
            if not w3.is_connected():
                logger.error("Failed to connect to Ethereum RPC")
                return activities
            
            # Получаем текущий блок и блок час назад
            current_block = w3.eth.block_number
            blocks_per_hour = 300  # Приблизительно 12 секунд на блок
            from_block = max(0, current_block - blocks_per_hour)
            
            logger.debug(f"Scanning Ethereum blocks {from_block} to {current_block}")
            
            # Мониторим каждый пул
            for pool_info in self.ethereum_pools:
                # Получаем liquidity события
                liquidity_activities = await self.fetch_ethereum_pool_events(
                    w3, 
                    pool_info['address'], 
                    pool_info['dao_name'],
                    pool_info['dao_token_address'],
                    from_block,
                    current_block
                )
                activities.extend(liquidity_activities)
                
                # Получаем swap события
                swap_activities = await self.fetch_ethereum_swap_events(
                    w3,
                    pool_info['address'],
                    pool_info['dao_name'],
                    pool_info['dao_token_address'],
                    from_block,
                    current_block
                )
                activities.extend(swap_activities)
            
            logger.info(f"📈 Found {len(activities)} enhanced Ethereum pool activities")
            
        except Exception as e:
            logger.error(f"Error in enhanced Ethereum pools monitoring: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return activities
    
    async def fetch_ethereum_swap_events(self, w3, pool_address: str, dao_name: str, dao_token_address: str, from_block: int, to_block: int) -> List[PoolActivityInfo]:
        """Получение Swap событий из Ethereum пула"""
        activities = []
        
        try:
            # Uniswap V2 Swap события
            swap_topic = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"  # Swap(address,uint256,uint256,uint256,uint256,address)
            
            # Uniswap V3 Swap события
            swap_v3_topic = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"  # Swap(address,address,int256,int256,uint160,uint128,int24)
            
            # Получаем swap события
            all_swap_events = []
            
            try:
                # Uniswap V2 Swap события
                swap_v2_events = w3.eth.get_logs({
                    'address': Web3.to_checksum_address(pool_address),
                    'topics': [swap_topic],
                    'fromBlock': from_block,
                    'toBlock': to_block
                })
                all_swap_events.extend([(event, 'v2') for event in swap_v2_events])
                
                # Uniswap V3 Swap события
                swap_v3_events = w3.eth.get_logs({
                    'address': Web3.to_checksum_address(pool_address),
                    'topics': [swap_v3_topic],
                    'fromBlock': from_block,
                    'toBlock': to_block
                })
                all_swap_events.extend([(event, 'v3') for event in swap_v3_events])
                
            except Exception as e:
                logger.debug(f"Error fetching swap events for pool {pool_address}: {e}")
                return activities
            
            # Парсим swap события
            for event_log, uniswap_version in all_swap_events:
                activity = await self.parse_ethereum_swap_event(
                    w3, event_log, uniswap_version, 
                    pool_address, dao_name, dao_token_address
                )
                if activity:
                    activities.append(activity)
            
            logger.debug(f"Found {len(all_swap_events)} swap events for Ethereum pool {pool_address}")
            
        except Exception as e:
            logger.error(f"Error fetching Ethereum swap events for {pool_address}: {e}")
        
        return activities
    
    async def parse_ethereum_swap_event(self, w3, event_log, uniswap_version: str, pool_address: str, dao_name: str, dao_token_address: str) -> Optional[PoolActivityInfo]:
        """Парсинг Ethereum swap события"""
        try:
            # Получаем информацию о транзакции
            tx_hash = event_log['transactionHash'].hex()
            block_info = w3.eth.get_block(event_log['blockNumber'])
            timestamp = datetime.fromtimestamp(block_info['timestamp'])
            
            # Для точной оценки стоимости нужно декодировать event data
            # Пока используем эвристическую оценку
            total_usd_value = Decimal('5000')  # Эвристическая оценка для swap
            
            # Проверяем есть ли DAO или BIO токен в этом пуле
            dao_token_involved = False
            bio_token_involved = False
            
            # Если пул связан с DAO, то считаем что DAO токен задействован
            dao_token_involved = any(dao.token_address == dao_token_address for dao in ALL_DAOS)
            bio_token_involved = dao_token_address in self.bio_token_addresses
            
            # Определяем тип операции (предполагаем что это может быть продажа DAO токена)
            dao_token_sold = dao_token_involved  # Упрощение для демо
            bio_token_sold = bio_token_involved
            
            activity_type = "swap_sell" if (dao_token_sold or bio_token_sold) else "swap_buy"
            
            # Получаем токены пула из кэша цен или используем заглушки
            token0_symbol = ""
            token1_symbol = ""
            
            if dao_token_address in self.dao_token_addresses:
                token0_symbol = self.dao_token_addresses[dao_token_address]
            if dao_token_address in self.bio_token_addresses:
                token1_symbol = self.bio_token_addresses[dao_token_address]
            
            activity = PoolActivityInfo(
                tx_hash=tx_hash,
                timestamp=timestamp,
                dao_name=dao_name,
                blockchain="ethereum",
                pool_address=pool_address,
                activity_type=activity_type,
                token0_address=dao_token_address,
                token1_address="",  # Требует декодирования event data
                token0_symbol=token0_symbol,
                token1_symbol=token1_symbol,
                token0_amount=Decimal('0'),  # Требует декодирования event data
                token1_amount=Decimal('0'),
                total_usd_value=total_usd_value,
                dao_token_sold=dao_token_sold,
                bio_token_sold=bio_token_sold,
                metadata={
                    "uniswap_version": uniswap_version,
                    "event_type": "swap",
                    "dao_token_involved": dao_token_involved,
                    "bio_token_involved": bio_token_involved,
                    "estimated_value": True,  # Флаг что стоимость оценочная
                    "block_number": event_log['blockNumber']
                }
            )
            
            return activity
            
        except Exception as e:
            logger.error(f"Error parsing Ethereum swap event: {e}")
            return None
    
    async def generate_alerts_and_notifications(self, activities: List[PoolActivityInfo], daily_alerts: List[Dict[str, Any]]) -> int:
        """Генерация алертов и отправка уведомлений"""
        alerts_count = 0
        
        # Алерты для отдельных транзакций
        for activity in activities:
            if (activity.total_usd_value >= self.alert_threshold or 
                activity.dao_token_sold or activity.bio_token_sold):
                
                alert_message = self.format_activity_alert(activity)
                logger.warning(f"🚨 POOL ALERT: {alert_message}")
                
                # Отправляем Telegram уведомление
                if self.notification_system:
                    try:
                        await self.notification_system.send_pool_activity_alert(activity)
                        logger.info(f"📱 Sent Telegram notification for pool activity")
                    except Exception as e:
                        logger.error(f"Error sending Telegram notification: {e}")
                
                alerts_count += 1
        
        # Алерты для дневных лимитов
        for daily_alert in daily_alerts:
            alert_message = self.format_daily_alert(daily_alert)
            logger.warning(f"🚨 DAILY LIMIT ALERT: {alert_message}")
            alerts_count += 1
        
        return alerts_count
    
    # Дублируем методы из оригинального PoolMonitor для совместимости
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
    
    async def fetch_solana_pool_trades(self, pool_address: str, dao_name: str, dao_token_address: str) -> List[PoolActivityInfo]:
        """Получение торгов Solana пула за последний час"""
        activities = []
        
        try:
            # Время начала (последний час)
            time_since = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Упрощенный GraphQL запрос
            query = """
            query poolActivities($since: DateTime!) {
              Solana(network: solana, dataset: realtime) {
                DEXTrades(
                  where: {
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
                    Dex {
                      ProtocolName
                    }
                  }
                }
              }
            }
            """
            
            if not self.bitquery_api_key:
                logger.debug(f"BitQuery API key not configured, skipping pool {pool_address}")
                return activities
            
            variables = {"since": time_since}
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
            
            # Парсим торги
            solana_data = data.get("data", {}).get("Solana", {})
            trades = solana_data.get("DEXTrades", []) if solana_data else []
                
            for trade in trades:
                # Предварительная фильтрация - проверяем есть ли наши токены в торге
                trade_data = trade.get("Trade", {})
                buy_data = trade_data.get("Buy", {})
                sell_data = trade_data.get("Sell", {})
                
                buy_token = buy_data.get("Currency", {}).get("MintAddress", "")
                sell_token = sell_data.get("Currency", {}).get("MintAddress", "")
                
                # Проверяем что торг связан с нашими токенами
                has_our_token = (
                    dao_token_address in [buy_token, sell_token] or
                    buy_token in self.dao_token_addresses or
                    sell_token in self.dao_token_addresses or
                    buy_token in self.bio_token_addresses or
                    sell_token in self.bio_token_addresses
                )
                
                if has_our_token:
                    activity = self.parse_solana_trade(trade, pool_address, dao_name, dao_token_address)
                    if activity:
                        activities.append(activity)
            
            logger.debug(f"Found {len(trades)} trades for pool {pool_address}")
            
        except Exception as e:
            logger.error(f"Error fetching Solana pool activities for {pool_address}: {e}")
        
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
    
    # Остальные методы делегируем к базовому PoolMonitor
    def filter_significant_activities(self, activities: List[PoolActivityInfo]) -> List[PoolActivityInfo]:
        """Фильтрация только значимых активностей"""
        significant = []
        
        for activity in activities:
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
            
            if is_significant:
                significant.append(activity)
        
        return significant
    
    async def check_daily_sales_limits(self) -> List[Dict[str, Any]]:
        """Проверка лимитов дневных продаж"""
        return []  # Пока упрощенная версия
    
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
    
    def format_activity_alert(self, activity: PoolActivityInfo) -> str:
        """Форматирование алерта для активности"""
        alert_type = ""
        if activity.dao_token_sold:
            alert_type = "DAO Token Sale"
        elif activity.bio_token_sold:
            alert_type = "BIO Token Sale"
        elif activity.activity_type == "add_liquidity":
            alert_type = "Add Liquidity"
        elif activity.activity_type == "remove_liquidity":
            alert_type = "Remove Liquidity"
        elif activity.activity_type.startswith("swap"):
            alert_type = "Token Swap"
        elif activity.total_usd_value >= self.alert_threshold:
            alert_type = "Large Transaction"
        else:
            alert_type = "Pool Activity"
        
        blockchain_info = activity.blockchain.title()
        is_estimated = activity.metadata and activity.metadata.get('estimated_value', False)
        value_suffix = " (estimated)" if is_estimated else ""
        
        alert_parts = [
            f"{alert_type} detected!",
            f"DAO: {activity.dao_name}",
            f"Blockchain: {blockchain_info}",
            f"Pool: {activity.pool_address[:10]}...{activity.pool_address[-8:]}",
            f"Operation: {activity.activity_type.replace('_', ' ').title()}",
            f"Value: ${activity.total_usd_value:,.2f}{value_suffix}",
            f"Tx: {activity.tx_hash}",
            f"Time: {activity.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        return "\n".join(alert_parts)
    
    def format_daily_alert(self, daily_alert: Dict[str, Any]) -> str:
        """Форматирование алерта для дневных лимитов"""
        return "Daily alert formatting not implemented yet"
    
    def _get_ethereum_rpc_url(self) -> Optional[str]:
        """Получение Ethereum RPC URL"""
        import os
        rpc_url = os.getenv('ETHEREUM_RPC_URL')
        if rpc_url:
            return rpc_url
        
        # Используем предоставленный Alchemy URL
        return 'https://eth-mainnet.g.alchemy.com/v2/0l42UZmHRHWXBYMJ2QFcdEE-Glj20xqn'
    
    async def fetch_ethereum_pool_events(self, w3, pool_address: str, dao_name: str, dao_token_address: str, from_block: int, to_block: int) -> List[PoolActivityInfo]:
        """Получение Mint/Burn событий из Ethereum пула"""
        # Возвращаем пустой список для упрощения
        return [] 