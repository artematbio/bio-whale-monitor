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
            # 3. Add/Remove liquidity > $10K (включая эвристические оценки)
            
            is_significant = False
            is_estimated_value = activity.metadata and activity.metadata.get('estimated_value', False)
            
            # Крупная транзакция
            if activity.total_usd_value >= self.alert_threshold:
                is_significant = True
                value_type = "estimated" if is_estimated_value else "actual"
                logger.info(f"🚨 Large transaction: ${activity.total_usd_value} ({value_type}) in {activity.dao_name} pool")
            
            # Продажа DAO или BIO токена
            if activity.dao_token_sold or activity.bio_token_sold:
                is_significant = True
                token_type = "DAO" if activity.dao_token_sold else "BIO"
                logger.info(f"📉 {token_type} token sale: ${activity.total_usd_value} in {activity.dao_name} pool")
            
            # Add/Remove liquidity операции
            if activity.activity_type in ['add_liquidity', 'remove_liquidity']:
                # Для liquidity операций учитываем эвристические оценки
                if activity.total_usd_value >= self.alert_threshold or is_estimated_value:
                    is_significant = True
                    value_info = f"${activity.total_usd_value} (estimated)" if is_estimated_value else f"${activity.total_usd_value}"
                    logger.info(f"💧 Large liquidity operation: {activity.activity_type} {value_info} in {activity.dao_name}")
            
            # Специальная логика для Raydium и Uniswap операций с DAO/BIO токенами
            if activity.metadata:
                dao_involved = activity.metadata.get('dao_token_involved', False)
                bio_involved = activity.metadata.get('bio_token_involved', False)
                
                if (dao_involved or bio_involved) and activity.activity_type in ['add_liquidity', 'remove_liquidity']:
                    is_significant = True
                    token_type = "DAO" if dao_involved else "BIO"
                    blockchain = activity.blockchain.title()
                    logger.info(f"🔗 {token_type} token liquidity operation: {activity.activity_type} on {blockchain} ({activity.dao_name})")
            
            if is_significant:
                significant.append(activity)
                # Обновляем дневную статистику продаж (только для swap операций, не для liquidity)
                if activity.activity_type in ['swap_sell', 'swap_buy']:
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
        """Мониторинг Ethereum пулов через Web3"""
        activities = []
        
        try:
            logger.info(f"🔍 Monitoring {len(self.ethereum_pools)} Ethereum pools")
            
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
                pool_activities = await self.fetch_ethereum_pool_events(
                    w3, 
                    pool_info['address'], 
                    pool_info['dao_name'],
                    pool_info['dao_token_address'],
                    from_block,
                    current_block
                )
                activities.extend(pool_activities)
            
            logger.info(f"📈 Found {len(activities)} Ethereum pool activities")
            
        except Exception as e:
            logger.error(f"Error monitoring Ethereum pools: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return activities
    
    def _get_ethereum_rpc_url(self) -> Optional[str]:
        """Получение Ethereum RPC URL"""
        import os
        rpc_url = os.getenv('ETHEREUM_RPC_URL')
        if rpc_url:
            return rpc_url
        
        # Временный фикс для Railway - используем hardcoded URL если в Railway
        if os.getenv('RAILWAY_ENVIRONMENT'):
            return 'https://eth-mainnet.g.alchemy.com/v2/0l42UZmHRHWXBYMJ2QFcdEE-Glj20xqn'
        
        # Для локальной разработки используем предоставленный Alchemy URL
        return 'https://eth-mainnet.g.alchemy.com/v2/0l42UZmHRHWXBYMJ2QFcdEE-Glj20xqn'
    
    async def fetch_ethereum_pool_events(self, w3, pool_address: str, dao_name: str, dao_token_address: str, from_block: int, to_block: int) -> List[PoolActivityInfo]:
        """Получение Mint/Burn событий из Ethereum пула"""
        activities = []
        
        try:
            # Uniswap V2 события
            mint_topic = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"  # Mint(address,uint256,uint256)
            burn_topic = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"  # Burn(address,uint256,uint256,address)
            
            # Uniswap V3 события
            mint_v3_topic = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"  # Mint(address,address,int24,int24,uint128,uint256,uint256)
            burn_v3_topic = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"  # Burn(address,int24,int24,uint128,uint256,uint256)
            
            # Получаем все события Mint и Burn
            all_events = []
            
            try:
                # Uniswap V2 Mint события
                mint_events = w3.eth.get_logs({
                    'address': Web3.to_checksum_address(pool_address),
                    'topics': [mint_topic],
                    'fromBlock': from_block,
                    'toBlock': to_block
                })
                all_events.extend([(event, 'add_liquidity', 'v2') for event in mint_events])
                
                # Uniswap V2 Burn события
                burn_events = w3.eth.get_logs({
                    'address': Web3.to_checksum_address(pool_address),
                    'topics': [burn_topic],
                    'fromBlock': from_block,
                    'toBlock': to_block
                })
                all_events.extend([(event, 'remove_liquidity', 'v2') for event in burn_events])
                
                # Uniswap V3 Mint события
                mint_v3_events = w3.eth.get_logs({
                    'address': Web3.to_checksum_address(pool_address),
                    'topics': [mint_v3_topic],
                    'fromBlock': from_block,
                    'toBlock': to_block
                })
                all_events.extend([(event, 'add_liquidity', 'v3') for event in mint_v3_events])
                
                # Uniswap V3 Burn события
                burn_v3_events = w3.eth.get_logs({
                    'address': Web3.to_checksum_address(pool_address),
                    'topics': [burn_v3_topic],
                    'fromBlock': from_block,
                    'toBlock': to_block
                })
                all_events.extend([(event, 'remove_liquidity', 'v3') for event in burn_v3_events])
                
            except Exception as e:
                logger.debug(f"Error fetching events for pool {pool_address}: {e}")
                return activities
            
            # Парсим события
            for event_log, activity_type, uniswap_version in all_events:
                activity = await self.parse_ethereum_liquidity_event(
                    w3, event_log, activity_type, uniswap_version, 
                    pool_address, dao_name, dao_token_address
                )
                if activity:
                    activities.append(activity)
            
            logger.debug(f"Found {len(all_events)} liquidity events for Ethereum pool {pool_address}")
            
        except Exception as e:
            logger.error(f"Error fetching Ethereum pool events for {pool_address}: {e}")
        
        return activities
    
    async def parse_ethereum_liquidity_event(self, w3, event_log, activity_type: str, uniswap_version: str, pool_address: str, dao_name: str, dao_token_address: str) -> Optional[PoolActivityInfo]:
        """Парсинг Ethereum liquidity события"""
        try:
            # Получаем информацию о транзакции
            tx_hash = event_log['transactionHash'].hex()
            block_info = w3.eth.get_block(event_log['blockNumber'])
            timestamp = datetime.fromtimestamp(block_info['timestamp'])
            
            # Для точной оценки стоимости нужно декодировать event data
            # Пока используем эвристическую оценку
            total_usd_value = Decimal('0')
            
            # Проверяем есть ли DAO или BIO токен в этом пуле
            dao_token_involved = False
            bio_token_involved = False
            
            # Если пул связан с DAO, то считаем что DAO токен задействован
            dao_token_involved = any(dao.token_address == dao_token_address for dao in ALL_DAOS)
            bio_token_involved = dao_token_address in self.bio_token_addresses
            
            if dao_token_involved or bio_token_involved:
                # Для пулов с DAO/BIO токенами, оценочная стоимость операции
                total_usd_value = Decimal('8000')  # Эвристическая оценка для Ethereum
            
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
                dao_token_sold=False,  # Liquidity операции не являются продажами
                bio_token_sold=False,
                metadata={
                    "uniswap_version": uniswap_version,
                    "event_type": activity_type,
                    "dao_token_involved": dao_token_involved,
                    "bio_token_involved": bio_token_involved,
                    "estimated_value": True,  # Флаг что стоимость оценочная
                    "block_number": event_log['blockNumber']
                }
            )
            
            return activity
            
        except Exception as e:
            logger.error(f"Error parsing Ethereum liquidity event: {e}")
            return None
    
    async def fetch_solana_pool_trades(self, pool_address: str, dao_name: str, dao_token_address: str) -> List[PoolActivityInfo]:
        """Получение торгов и liquidity операций Solana пула за последний час"""
        activities = []
        
        try:
            # Время начала (последний час)
            time_since = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Упрощенный GraphQL запрос только для торгов (убираем Instructions пока что)
            query = """
            query poolActivities($since: DateTime!) {
              Solana(network: solana, dataset: realtime) {
                # Получаем торги (swaps)
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
            
            # Отладочный вывод для проверки структуры ответа
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"BitQuery response for pool {pool_address}: {json.dumps(data, indent=2)[:500]}...")
            
            solana_data = data.get("data", {})
            if solana_data is None:
                logger.debug(f"No data returned from BitQuery for pool {pool_address}")
                return activities
            
            solana_data = solana_data.get("Solana", {})
            if solana_data is None:
                logger.debug(f"No Solana data returned from BitQuery for pool {pool_address}")
                return activities
            
            # Парсим торги
            trades = solana_data.get("DEXTrades", [])
            if trades is None:
                logger.debug(f"No trades data returned for pool {pool_address}")
                trades = []
                
            for trade in trades:
                # Предварительная фильтрация - проверяем есть ли наши токены в торге
                trade_data = trade.get("Trade", {})
                buy_data = trade_data.get("Buy", {})
                sell_data = trade_data.get("Sell", {})
                
                buy_token = buy_data.get("Currency", {}).get("MintAddress", "")
                sell_token = sell_data.get("Currency", {}).get("MintAddress", "")
                buy_symbol = buy_data.get("Currency", {}).get("Symbol", "")
                sell_symbol = sell_data.get("Currency", {}).get("Symbol", "")
                
                # Проверяем что торг связан с нашими токенами
                has_our_token = (
                    dao_token_address in [buy_token, sell_token] or
                    buy_token in self.dao_token_addresses or
                    sell_token in self.dao_token_addresses or
                    buy_token in self.bio_token_addresses or
                    sell_token in self.bio_token_addresses or
                    'BIO' in [buy_symbol, sell_symbol] or
                    dao_name.upper() in buy_symbol.upper() or
                    dao_name.upper() in sell_symbol.upper()
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
        elif activity.activity_type == "add_liquidity":
            alert_type = "Add Liquidity"
        elif activity.activity_type == "remove_liquidity":
            alert_type = "Remove Liquidity"
        elif activity.total_usd_value >= self.alert_threshold:
            alert_type = "Large Transaction"
        else:
            alert_type = "Pool Activity"
        
        # Определяем дополнительную информацию
        blockchain_info = activity.blockchain.title()
        is_estimated = activity.metadata and activity.metadata.get('estimated_value', False)
        value_suffix = " (estimated)" if is_estimated else ""
        
        # Специальная информация для разных типов операций
        operation_info = ""
        if activity.activity_type in ["add_liquidity", "remove_liquidity"]:
            if activity.metadata:
                if activity.metadata.get('uniswap_version'):
                    operation_info = f"Uniswap {activity.metadata['uniswap_version'].upper()}"
                elif activity.metadata.get('program_name'):
                    operation_info = activity.metadata['program_name']
        
        token_info = ""
        if activity.token0_symbol and activity.token1_symbol:
            token_info = f"Tokens: {activity.token0_symbol} ↔ {activity.token1_symbol}"
        elif activity.token0_symbol:
            token_info = f"Token: {activity.token0_symbol}"
        
        alert_parts = [
            f"{alert_type} detected!",
            f"DAO: {activity.dao_name}",
            f"Blockchain: {blockchain_info}",
            f"Pool: {activity.pool_address[:10]}...{activity.pool_address[-8:]}",
            f"Operation: {activity.activity_type.replace('_', ' ').title()}"
        ]
        
        if operation_info:
            alert_parts.append(f"Protocol: {operation_info}")
        
        if token_info:
            alert_parts.append(token_info)
        
        alert_parts.extend([
            f"Value: ${activity.total_usd_value:,.2f}{value_suffix}",
            f"Tx: {activity.tx_hash}",
            f"Time: {activity.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        return "\n".join(alert_parts)
    
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