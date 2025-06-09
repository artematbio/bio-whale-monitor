#!/usr/bin/env python3
"""
Solana мониторинг для DAO Treasury
Использует Helius API для отслеживания транзакций treasury адресов
"""

import asyncio
import aiohttp
import httpx
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import os
from dataclasses import dataclass

from config.dao_config import SOLANA_DAOS, BIO_TOKEN_SOLANA, get_dao_by_treasury_address
from database.database import DAOTreasuryDatabase
from utils.price_utils import get_token_price_coingecko, get_multiple_token_prices

logger = logging.getLogger(__name__)

@dataclass
class SolanaTransactionInfo:
    """Информация о Solana транзакции"""
    signature: str
    timestamp: datetime
    from_address: str
    to_address: str
    token_address: str
    amount: Decimal
    amount_usd: Decimal
    tx_type: str
    metadata: Dict[str, Any]

class SolanaMonitor:
    """Мониторинг Solana treasury транзакций"""
    
    def __init__(self, api_key: str, database: DAOTreasuryDatabase):
        self.api_key = api_key
        self.base_url = "https://mainnet.helius-rpc.com"
        self.database = database
        self.session = None
        self.http_client = None
        
        # Настройки мониторинга
        self.check_interval = 30  # Проверка каждые 30 секунд
        self.batch_size = 1000   # Максимум транзакций за запрос
        self.alert_threshold = Decimal("10000")  # $10,000 порог алерта
        
        # Кэш для оптимизации
        self.token_prices_cache = {}
        self.price_cache_ttl = 300  # 5 минут
        self.last_price_update = 0
        
        # Treasury адреса для мониторинга
        self.treasury_addresses = [dao.treasury_address for dao in SOLANA_DAOS]
        
        logger.info(f"Initialized Solana monitor for {len(self.treasury_addresses)} treasury addresses")
    
    async def start_session(self):
        """Инициализация HTTP сессий"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close_session(self):
        """Закрытие HTTP сессий"""
        if self.session:
            await self.session.close()
            self.session = None
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def get_account_transactions(self, address: str, limit: int = 100, before: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение транзакций аккаунта через Helius API"""
        try:
            url = f"{self.base_url}/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "getSignaturesForAddress",
                "params": [
                    address,
                    {
                        "limit": limit,
                        "before": before
                    }
                ]
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        return data['result']
                    else:
                        logger.error(f"No result in response for {address}: {data}")
                        return []
                else:
                    logger.error(f"HTTP error {response.status} for address {address}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {e}")
            return []
    
    async def get_transaction_details(self, signature: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о транзакции"""
        try:
            url = f"{self.base_url}/?api-key={self.api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": "1", 
                "method": "getTransaction",
                "params": [
                    signature,
                    {
                        "encoding": "json",
                        "commitment": "confirmed",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data and data['result']:
                        return data['result']
                    else:
                        logger.debug(f"No transaction data for signature {signature}")
                        return None
                else:
                    logger.error(f"HTTP error {response.status} for signature {signature}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting transaction details for {signature}: {e}")
            return None
    
    async def get_token_price_async(self, token_address: str) -> Decimal:
        """Асинхронное получение цены токена с кэшированием"""
        current_time = time.time()
        
        # Проверка кэша
        if (token_address in self.token_prices_cache and 
            current_time - self.last_price_update < self.price_cache_ttl):
            return self.token_prices_cache[token_address]
        
        try:
            # Обновление кэша цен
            if current_time - self.last_price_update >= self.price_cache_ttl:
                # Собираем все адреса токенов для батчевого запроса
                token_addresses = [dao.token_address for dao in SOLANA_DAOS] + [BIO_TOKEN_SOLANA]
                
                # Получаем цены пакетом через новую функцию
                prices = await get_multiple_token_prices(token_addresses, 'solana', self.http_client)
                
                # Обновляем кэш
                for addr, price in prices.items():
                    self.token_prices_cache[addr] = price
                
                self.last_price_update = current_time
            
            return self.token_prices_cache.get(token_address, Decimal('0'))
            
        except Exception as e:
            logger.error(f"Error getting token price for {token_address}: {e}")
            # Попробуем получить индивидуально как fallback
            try:
                price = await get_token_price_coingecko(token_address, 'solana', self.http_client)
                self.token_prices_cache[token_address] = price
                return price
            except Exception as e2:
                logger.error(f"Fallback price fetch also failed for {token_address}: {e2}")
                return Decimal('0')
    
    def parse_token_transfer(self, tx_data: Dict[str, Any], treasury_address: str) -> List[SolanaTransactionInfo]:
        """Парсинг токен трансферов из транзакции"""
        transfers = []
        
        try:
            if not tx_data.get('meta') or not tx_data.get('transaction'):
                return transfers
            
            meta = tx_data['meta']
            transaction = tx_data['transaction']
            
            # Проверяем токен балансы до и после транзакции
            pre_balances = meta.get('preTokenBalances', [])
            post_balances = meta.get('postTokenBalances', [])
            
            # Группируем балансы по аккаунту и токену
            balance_changes = {}
            
            for balance in pre_balances:
                account = balance.get('owner', '')
                mint = balance.get('mint', '')
                ui_amount = balance.get('uiTokenAmount', {}).get('uiAmount')
                amount = Decimal(str(ui_amount)) if ui_amount is not None else Decimal('0')
                
                key = f"{account}:{mint}"
                if key not in balance_changes:
                    balance_changes[key] = {'pre': amount, 'post': Decimal('0'), 'mint': mint, 'account': account}
                else:
                    balance_changes[key]['pre'] = amount
            
            for balance in post_balances:
                account = balance.get('owner', '')
                mint = balance.get('mint', '')
                ui_amount = balance.get('uiTokenAmount', {}).get('uiAmount')
                amount = Decimal(str(ui_amount)) if ui_amount is not None else Decimal('0')
                
                key = f"{account}:{mint}"
                if key not in balance_changes:
                    balance_changes[key] = {'pre': Decimal('0'), 'post': amount, 'mint': mint, 'account': account}
                else:
                    balance_changes[key]['post'] = amount
            
            # Находим трансферы с участием treasury
            timestamp = datetime.fromtimestamp(tx_data.get('blockTime', time.time()))
            signature = tx_data['transaction']['signatures'][0]
            
            for key, change in balance_changes.items():
                account = change['account']
                mint = change['mint']
                amount_change = change['post'] - change['pre']
                
                # Игнорируем незначительные изменения
                if abs(amount_change) < Decimal('0.001'):
                    continue
                
                # Проверяем, связан ли трансфер с treasury
                if account.lower() == treasury_address.lower():
                    
                    # Определяем направление и партнера
                    if amount_change < 0:  # Исходящий трансфер
                        from_address = treasury_address
                        to_address = "unknown"  # Нужно найти получателя
                        tx_type = "outgoing"
                    else:  # Входящий трансфер
                        from_address = "unknown"  # Нужно найти отправителя
                        to_address = treasury_address
                        tx_type = "incoming"
                    
                    transfer_info = SolanaTransactionInfo(
                        signature=signature,
                        timestamp=timestamp,
                        from_address=from_address,
                        to_address=to_address,
                        token_address=mint,
                        amount=abs(amount_change),
                        amount_usd=Decimal('0'),  # Будет рассчитана позже
                        tx_type=tx_type,
                        metadata={
                            'block_time': tx_data.get('blockTime'),
                            'slot': tx_data.get('slot'),
                            'fee': meta.get('fee', 0),
                            'success': meta.get('err') is None
                        }
                    )
                    
                    transfers.append(transfer_info)
            
        except Exception as e:
            logger.error(f"Error parsing token transfer: {e}")
        
        return transfers
    
    async def process_transaction(self, signature: str, treasury_address: str) -> List[SolanaTransactionInfo]:
        """Обработка отдельной транзакции"""
        try:
            # Проверяем, была ли транзакция уже обработана
            if self.database.is_transaction_processed(signature):
                logger.debug(f"Transaction {signature} already processed, skipping")
                return []
            
            # Получаем детали транзакции
            tx_data = await self.get_transaction_details(signature)
            if not tx_data:
                return []
            
            # Парсим трансферы
            transfers = self.parse_token_transfer(tx_data, treasury_address)
            
            # Обогащаем данные ценами и USD суммами
            for transfer in transfers:
                price = await self.get_token_price_async(transfer.token_address)
                transfer.amount_usd = transfer.amount * price
            
            return transfers
            
        except Exception as e:
            logger.error(f"Error processing transaction {signature}: {e}")
            return []
    
    async def monitor_treasury_address(self, treasury_address: str) -> List[SolanaTransactionInfo]:
        """Мониторинг отдельного treasury адреса"""
        logger.info(f"Monitoring Solana treasury: {treasury_address}")
        
        all_transfers = []
        
        try:
            # Получаем последние транзакции
            transactions = await self.get_account_transactions(treasury_address, limit=50)
            
            if not transactions:
                logger.debug(f"No transactions found for {treasury_address}")
                return all_transfers
            
            # Обрабатываем каждую транзакцию
            for tx in transactions:
                signature = tx.get('signature', '')
                if not signature:
                    continue
                
                # Проверяем время транзакции (не старше 24 часов)
                block_time = tx.get('blockTime')
                if block_time:
                    tx_time = datetime.fromtimestamp(block_time)
                    if datetime.now() - tx_time > timedelta(hours=24):
                        logger.debug(f"Transaction {signature} too old, skipping")
                        continue
                
                # Проверяем успешность транзакции
                if tx.get('err'):
                    logger.debug(f"Transaction {signature} failed, skipping")
                    continue
                
                # Обрабатываем транзакцию
                transfers = await self.process_transaction(signature, treasury_address)
                all_transfers.extend(transfers)
            
        except Exception as e:
            logger.error(f"Error monitoring treasury {treasury_address}: {e}")
        
        return all_transfers
    
    async def save_transfers_to_database(self, transfers: List[SolanaTransactionInfo], dao_name: str):
        """Сохранение трансферов в базу данных"""
        for transfer in transfers:
            try:
                # Подготавливаем данные для сохранения
                tx_data = {
                    'tx_hash': transfer.signature,
                    'timestamp': transfer.timestamp,
                    'dao_name': dao_name,
                    'blockchain': 'solana',
                    'from_address': transfer.from_address,
                    'to_address': transfer.to_address,
                    'token_address': transfer.token_address,
                    'token_symbol': 'UNKNOWN',  # Получим позже
                    'amount': transfer.amount,
                    'amount_usd': transfer.amount_usd,
                    'tx_type': transfer.tx_type,
                    'alert_triggered': transfer.amount_usd >= self.alert_threshold,
                    'metadata': transfer.metadata
                }
                
                # Получаем символ токена из DAO конфигурации
                dao_config = get_dao_by_treasury_address(transfer.to_address if transfer.tx_type == 'incoming' else transfer.from_address)
                if dao_config and transfer.token_address == dao_config.token_address:
                    tx_data['token_symbol'] = dao_config.token_symbol
                elif transfer.token_address == BIO_TOKEN_SOLANA:
                    tx_data['token_symbol'] = 'BIO'
                
                # Сохраняем в базу данных
                success = self.database.save_treasury_transaction(tx_data)
                
                if success and tx_data['alert_triggered']:
                    # Создаем алерт для крупных транзакций
                    alert_data = {
                        'alert_type': 'large_transaction',
                        'dao_name': dao_name,
                        'severity': 'high' if transfer.amount_usd >= Decimal('50000') else 'medium',
                        'title': f'Large Solana Transaction - {dao_name}',
                        'message': f'{transfer.tx_type.title()} transfer of {transfer.amount:,.2f} {tx_data["token_symbol"]} (${transfer.amount_usd:,.2f})',
                        'tx_hash': transfer.signature,
                        'amount_usd': transfer.amount_usd,
                        'timestamp': transfer.timestamp
                    }
                    
                    self.database.save_alert(alert_data)
                    logger.warning(f"ALERT: Large transaction detected - {dao_name} - ${transfer.amount_usd:,.2f}")
                
            except Exception as e:
                logger.error(f"Error saving transfer to database: {e}")
    
    async def run_monitoring_cycle(self):
        """Один цикл мониторинга всех treasury адресов"""
        start_time = time.time()
        total_transfers = 0
        
        logger.info("Starting Solana monitoring cycle")
        
        try:
            await self.start_session()
            
            # Мониторим каждый DAO
            for dao in SOLANA_DAOS:
                try:
                    transfers = await self.monitor_treasury_address(dao.treasury_address)
                    
                    if transfers:
                        await self.save_transfers_to_database(transfers, dao.name)
                        total_transfers += len(transfers)
                        logger.info(f"Found {len(transfers)} new transfers for {dao.name}")
                    
                    # Небольшая задержка между запросами
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error monitoring DAO {dao.name}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
        
        finally:
            await self.close_session()
        
        duration = time.time() - start_time
        logger.info(f"Monitoring cycle completed in {duration:.2f}s - {total_transfers} transfers processed")
    
    async def start_monitoring(self):
        """Запуск непрерывного мониторинга"""
        logger.info("Starting continuous Solana monitoring")
        
        while True:
            try:
                await self.run_monitoring_cycle()
                
                # Ожидание до следующего цикла
                logger.debug(f"Waiting {self.check_interval} seconds until next cycle")
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке

if __name__ == "__main__":
    # Тестирование Solana мониторинга
    logging.basicConfig(level=logging.INFO)
    
    # Читаем API ключ из переменной окружения
    api_key = os.getenv('HELIUS_API_KEY', 'd4af7b72-f199-4d77-91a9-11d8512c5e42')
    
    if not api_key:
        logger.error("HELIUS_API_KEY not found in environment variables")
        exit(1)
    
    # Инициализируем базу данных
    database = DAOTreasuryDatabase()
    
    # Создаем мониторинг
    monitor = SolanaMonitor(api_key, database)
    
    # Запуск мониторинга
    try:
        asyncio.run(monitor.start_monitoring())
    except KeyboardInterrupt:
        logger.info("Solana monitoring stopped") 