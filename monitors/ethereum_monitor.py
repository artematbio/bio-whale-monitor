#!/usr/bin/env python3
"""
Ethereum мониторинг для DAO Treasury
Использует Alchemy API для отслеживания транзакций treasury адресов
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
from web3 import Web3

from config.dao_config import ETHEREUM_DAOS, BIO_TOKEN_ETHEREUM, get_dao_by_treasury_address
from database.database import DAOTreasuryDatabase
from utils.price_utils import get_token_price_coingecko, get_multiple_token_prices

logger = logging.getLogger(__name__)

@dataclass
class EthereumTransactionInfo:
    """Информация о Ethereum транзакции"""
    tx_hash: str
    timestamp: datetime
    from_address: str
    to_address: str
    token_address: str
    amount: Decimal
    amount_usd: Decimal
    tx_type: str
    gas_used: int
    gas_price: int
    metadata: Dict[str, Any]

class EthereumMonitor:
    """Мониторинг Ethereum treasury транзакций"""
    
    def __init__(self, rpc_url: str, database: DAOTreasuryDatabase, notification_system=None):
        self.rpc_url = rpc_url
        self.database = database
        self.notification_system = notification_system  # Добавляем систему уведомлений
        self.session = None
        self.http_client = None
        
        # Настройки мониторинга
        self.check_interval = 30  # Проверка каждые 30 секунд
        self.alert_threshold = Decimal("10000")  # $10,000 порог алерта
        self.blocks_to_check = 10  # Проверяем последние 10 блоков
        
        # Кэш для оптимизации
        self.token_prices_cache = {}
        self.price_cache_ttl = 300  # 5 минут
        self.last_price_update = 0
        self.last_processed_block = None
        
        # Treasury адреса для мониторинга
        self.treasury_addresses = [dao.treasury_address.lower() for dao in ETHEREUM_DAOS]
        
        logger.info(f"Initializing Ethereum monitor for {len(self.treasury_addresses)} treasury addresses")
        logger.info(f"Using RPC URL: {rpc_url[:50]}...")
        
        # Инициализируем Web3 с обработкой ошибок
        try:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            logger.info("Web3 provider created successfully")
            
            # Проверяем подключение
            latest_block = self.w3.eth.block_number
            logger.info(f"✅ Connected to Ethereum node. Latest block: {latest_block}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Ethereum node: {e}")
            logger.error(f"RPC URL: {rpc_url}")
            raise Exception(f"Ethereum connection failed: {e}")
    
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
    
    async def monitor_treasury_addresses(self):
        """Основной цикл мониторинга treasury адресов"""
        try:
            await self.start_session()
            
            start_time = time.time()
            logger.info("Starting Ethereum monitoring cycle")
            
            # Получаем последний блок
            latest_block_number = self.w3.eth.block_number
            logger.info(f"📊 Latest Ethereum block: {latest_block_number}")
            
            # Устанавливаем начальный блок если не установлен
            if self.last_processed_block is None:
                self.last_processed_block = latest_block_number - self.blocks_to_check
                logger.info(f"🔄 First run - starting from block {self.last_processed_block}")
            
            # Вычисляем блоки для обработки
            blocks_to_process = list(range(self.last_processed_block + 1, latest_block_number + 1))
            if blocks_to_process:
                logger.info(f"🔍 Processing {len(blocks_to_process)} new blocks: {blocks_to_process[0]} to {blocks_to_process[-1]}")
            else:
                logger.info("✅ No new blocks to process")
            
            # Проверяем новые блоки
            transfers_found = 0
            for block_num in blocks_to_process:
                logger.info(f"   🔍 Scanning block {block_num}...")
                block_transfers = await self.process_block(block_num)
                transfers_found += len(block_transfers)
                
                if block_transfers:
                    logger.info(f"   📝 Found {len(block_transfers)} transfers in block {block_num}")
                    await self.save_transfers_to_database(block_transfers)
                else:
                    logger.debug(f"   ✅ No relevant transfers in block {block_num}")
            
            # Логируем treasury адреса которые мониторим
            logger.info(f"🏛️ Monitoring {len(self.treasury_addresses)} treasury addresses:")
            for i, addr in enumerate(self.treasury_addresses, 1):
                dao_config = get_dao_by_treasury_address(addr)
                dao_name = dao_config.name if dao_config else "Unknown"
                logger.info(f"   {i}. {dao_name}: {addr}")
            
            self.last_processed_block = latest_block_number
            
            processing_time = time.time() - start_time
            logger.info(f"✅ Ethereum monitoring cycle completed in {processing_time:.2f}s - {transfers_found} transfers processed")
            
        except Exception as e:
            logger.error(f"❌ Error in Ethereum monitoring cycle: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        finally:
            await self.close_session()
    
    async def process_block(self, block_number: int) -> List[EthereumTransactionInfo]:
        """Обработка одного блока"""
        transfers = []
        
        try:
            # Получаем блок с транзакциями
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            block_timestamp = datetime.fromtimestamp(block.timestamp)
            
            # Проверяем каждую транзакцию в блоке
            for tx in block.transactions:
                # Проверяем только транзакции с нашими treasury адресами
                if (tx['from'] and tx['from'].lower() in self.treasury_addresses) or \
                   (tx['to'] and tx['to'].lower() in self.treasury_addresses):
                    
                    transfer_info = await self.parse_transaction(tx, block_timestamp)
                    if transfer_info:
                        transfers.append(transfer_info)
            
        except Exception as e:
            logger.error(f"Error processing block {block_number}: {e}")
        
        return transfers
    
    async def parse_transaction(self, tx, block_timestamp: datetime) -> Optional[EthereumTransactionInfo]:
        """Парсинг транзакции"""
        try:
            tx_hash = tx['hash'].hex()
            from_address = tx['from'] if tx['from'] else ""
            to_address = tx['to'] if tx['to'] else ""
            
            # Получаем receipt для проверки статуса
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            # Пропускаем неуспешные транзакции
            if receipt.status != 1:
                return None
            
            # Определяем тип транзакции
            tx_type = "unknown"
            token_address = "ETH"  # По умолчанию ETH
            amount = Decimal('0')
            
            # ETH transfer
            if tx['value'] > 0:
                amount = Decimal(str(self.w3.from_wei(tx['value'], 'ether')))
                token_address = "ETH"
                
                # Определяем направление
                if from_address.lower() in self.treasury_addresses:
                    tx_type = "outgoing_eth"
                elif to_address.lower() in self.treasury_addresses:
                    tx_type = "incoming_eth"
            
            # Проверяем ERC-20 transfers в логах
            erc20_transfers = self.parse_erc20_transfers(receipt.logs)
            for erc20_transfer in erc20_transfers:
                if (erc20_transfer['from'].lower() in self.treasury_addresses or 
                    erc20_transfer['to'].lower() in self.treasury_addresses):
                    
                    amount = erc20_transfer['amount']
                    token_address = erc20_transfer['token_address']
                    
                    if erc20_transfer['from'].lower() in self.treasury_addresses:
                        tx_type = "outgoing_token"
                        from_address = erc20_transfer['from']
                        to_address = erc20_transfer['to']
                    else:
                        tx_type = "incoming_token"
                        from_address = erc20_transfer['from']
                        to_address = erc20_transfer['to']
                    break
            
            # Пропускаем мелкие транзакции
            if amount < Decimal('0.001'):
                return None
            
            # Получаем цену токена в USD
            amount_usd = await self.get_token_price_usd(token_address, amount)
            
            transfer_info = EthereumTransactionInfo(
                tx_hash=tx_hash,
                timestamp=block_timestamp,
                from_address=from_address,
                to_address=to_address,
                token_address=token_address,
                amount=amount,
                amount_usd=amount_usd,
                tx_type=tx_type,
                gas_used=receipt.gasUsed,
                gas_price=tx['gasPrice'],
                metadata={
                    'block_number': tx['blockNumber'],
                    'block_hash': tx['blockHash'].hex(),
                    'transaction_index': tx['transactionIndex'],
                    'nonce': tx['nonce'],
                    'gas_limit': tx['gas']
                }
            )
            
            return transfer_info
            
        except Exception as e:
            logger.error(f"Error parsing transaction {tx_hash}: {e}")
            return None
    
    def parse_erc20_transfers(self, logs) -> List[Dict[str, Any]]:
        """Парсинг ERC-20 Transfer событий из логов"""
        transfers = []
        
        # ERC-20 Transfer event signature: Transfer(address,address,uint256)
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        for log in logs:
            if len(log.topics) >= 3 and log.topics[0].hex() == transfer_topic:
                try:
                    from_address = "0x" + log.topics[1].hex()[-40:]
                    to_address = "0x" + log.topics[2].hex()[-40:]
                    
                    # Получаем количество токенов
                    amount_raw = int(log.data.hex(), 16)
                    
                    # Получаем decimals токена (по умолчанию 18) - синхронно
                    decimals = self.get_token_decimals_sync(log.address)
                    amount = Decimal(amount_raw) / Decimal(10 ** decimals)
                    
                    transfers.append({
                        'from': from_address,
                        'to': to_address,
                        'amount': amount,
                        'token_address': log.address
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing ERC-20 transfer log: {e}")
        
        return transfers
    
    def get_token_decimals_sync(self, token_address: str) -> int:
        """Синхронное получение количества decimals для ERC-20 токена"""
        try:
            # Кэш для decimals
            if not hasattr(self, 'decimals_cache'):
                self.decimals_cache = {}
            
            if token_address in self.decimals_cache:
                return self.decimals_cache[token_address]
            
            # ERC-20 decimals() function selector
            decimals_selector = "0x313ce567"
            
            result = self.w3.eth.call({
                'to': token_address,
                'data': decimals_selector
            })
            
            decimals = int(result.hex(), 16)
            self.decimals_cache[token_address] = decimals
            return decimals
            
        except Exception as e:
            logger.debug(f"Error getting decimals for {token_address}: {e}")
            return 18  # По умолчанию 18 decimals
    
    async def get_token_price_usd(self, token_address: str, amount: Decimal) -> Decimal:
        """Получение цены токена в USD"""
        try:
            if token_address == "ETH":
                # Для ETH используем специальный адрес
                price = await get_token_price_coingecko("ethereum", 'ethereum', self.http_client)
            else:
                price = await get_token_price_coingecko(token_address, 'ethereum', self.http_client)
            
            return amount * price
            
        except Exception as e:
            logger.error(f"Error getting price for {token_address}: {e}")
            return Decimal('0')
    
    async def save_transfers_to_database(self, transfers: List[EthereumTransactionInfo]):
        """Сохранение трансферов в базу данных"""
        for transfer in transfers:
            try:
                # Определяем DAO
                dao_name = "Unknown"
                treasury_addr = transfer.from_address if transfer.tx_type.startswith('outgoing') else transfer.to_address
                dao_config = get_dao_by_treasury_address(treasury_addr)
                if dao_config:
                    dao_name = dao_config.name
                
                # Подготавливаем данные для сохранения
                tx_data = {
                    'tx_hash': transfer.tx_hash,
                    'timestamp': transfer.timestamp,
                    'dao_name': dao_name,
                    'blockchain': 'ethereum',
                    'from_address': transfer.from_address,
                    'to_address': transfer.to_address,
                    'token_address': transfer.token_address,
                    'token_symbol': self.get_token_symbol(transfer.token_address, dao_config),
                    'amount': transfer.amount,
                    'amount_usd': transfer.amount_usd,
                    'tx_type': transfer.tx_type,
                    'alert_triggered': transfer.amount_usd >= self.alert_threshold,
                    'metadata': transfer.metadata
                }
                
                # Сохраняем в базу данных
                success = self.database.save_treasury_transaction(tx_data)
                if success:
                    logger.info(f"Saved treasury transaction: {transfer.tx_hash} - {dao_name} - ${transfer.amount_usd:.2f}")
                    
                    # Логируем алерт если превышен порог
                    if transfer.amount_usd >= self.alert_threshold:
                        logger.warning(f"🚨 ALERT: Large transaction detected! {dao_name} - ${transfer.amount_usd:,.2f}")
                        
                        # Отправляем уведомление в Telegram
                        if self.notification_system:
                            try:
                                await self.notification_system.send_transaction_alert(tx_data)
                            except Exception as e:
                                logger.error(f"Failed to send Telegram alert: {e}")
                
            except Exception as e:
                logger.error(f"Error saving transfer {transfer.tx_hash}: {e}")
    
    def get_token_symbol(self, token_address: str, dao_config) -> str:
        """Получение символа токена"""
        if token_address == "ETH":
            return "ETH"
        elif token_address == BIO_TOKEN_ETHEREUM:
            return "BIO"
        elif dao_config and token_address.lower() == dao_config.token_address.lower():
            return dao_config.token_symbol
        else:
            return "UNKNOWN"
    
    async def get_treasury_balances(self) -> Dict[str, Dict[str, Decimal]]:
        """Получение текущих балансов treasury адресов"""
        balances = {}
        
        for treasury_addr in self.treasury_addresses:
            dao_config = get_dao_by_treasury_address(treasury_addr)
            dao_name = dao_config.name if dao_config else treasury_addr[:10]
            
            try:
                # ETH balance
                eth_balance_wei = self.w3.eth.get_balance(treasury_addr)
                eth_balance = Decimal(str(self.w3.from_wei(eth_balance_wei, 'ether')))
                
                balances[dao_name] = {
                    'ETH': eth_balance
                }
                
                # DAO token balance (если есть)
                if dao_config:
                    token_balance = await self.get_erc20_balance(treasury_addr, dao_config.token_address)
                    balances[dao_name][dao_config.token_symbol] = token_balance
                
                # BIO token balance
                bio_balance = await self.get_erc20_balance(treasury_addr, BIO_TOKEN_ETHEREUM)
                balances[dao_name]['BIO'] = bio_balance
                
            except Exception as e:
                logger.error(f"Error getting balance for {treasury_addr}: {e}")
        
        return balances
    
    async def get_erc20_balance(self, address: str, token_address: str) -> Decimal:
        """Получение баланса ERC-20 токена"""
        try:
            # ERC-20 balanceOf(address) function selector + address
            balance_selector = "0x70a08231"
            address_padded = address[2:].zfill(64)  # Убираем 0x и добавляем padding
            
            result = self.w3.eth.call({
                'to': token_address,
                'data': balance_selector + address_padded
            })
            
            balance_raw = int(result.hex(), 16)
            decimals = self.get_token_decimals_sync(token_address)
            balance = Decimal(balance_raw) / Decimal(10 ** decimals)
            
            return balance
            
        except Exception as e:
            logger.debug(f"Error getting ERC-20 balance for {address} {token_address}: {e}")
            return Decimal('0')

# Функция для использования в main.py
async def monitor_ethereum_treasury():
    """Функция мониторинга Ethereum treasury для использования в main.py"""
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    if not rpc_url:
        logger.error("ETHEREUM_RPC_URL environment variable not set")
        return
    
    from database.database import DAOTreasuryDatabase
    database = DAOTreasuryDatabase()
    
    monitor = EthereumMonitor(rpc_url, database)
    await monitor.monitor_treasury_addresses() 