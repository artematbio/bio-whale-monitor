#!/usr/bin/env python3
"""
BIO Whale Monitor
Мониторинг крупных исходящих транзакций BIO и vBIO токенов
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from web3 import Web3
from web3.contract import Contract
import json

from config.whale_config import (
    BIO_TOKENS, 
    WHALE_THRESHOLDS, 
    MONITORED_WALLETS,
    MONITORING_CONFIG,
    get_resolved_wallet_addresses,
    is_ens_domain
)
from utils.price_utils import get_bio_token_price, format_price
from notifications.notification_system import NotificationSystem

# ERC-20 Token ABI (минимальный набор для чтения трансферов)
ERC20_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class BIOWhaleMonitor:
    """Мониторинг крупных исходящих транзакций BIO и vBIO токенов"""
    
    def __init__(self, ethereum_rpc_url: str, database, notification_system: NotificationSystem):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.database = database
        self.notification_system = notification_system
        
        # Инициализация Web3
        try:
            self.w3 = Web3(Web3.HTTPProvider(ethereum_rpc_url))
            if not self.w3.is_connected():
                raise Exception("Cannot connect to Ethereum RPC")
            self.logger.info(f"✅ Connected to Ethereum RPC: {ethereum_rpc_url[:50]}...")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Ethereum RPC: {e}")
            raise
        
        # Инициализация контрактов токенов
        self.token_contracts = {}
        self._initialize_token_contracts()
        
        # Разрешение ENS доменов в адреса
        self.monitored_addresses = []
        self._resolve_wallet_addresses()
        
        # Кэш для хранения последних обработанных блоков
        self.last_processed_blocks = {}
        
        # Кэш цен токенов (обновляется каждые 5 минут)
        self.price_cache = {}
        self.last_price_update = 0
    
    def _initialize_token_contracts(self):
        """Инициализация контрактов BIO токенов"""
        for token_key, token_info in BIO_TOKENS.items():
            try:
                contract_address = Web3.to_checksum_address(token_info['contract_address'])
                contract = self.w3.eth.contract(
                    address=contract_address,
                    abi=ERC20_ABI
                )
                self.token_contracts[token_key] = {
                    'contract': contract,
                    'info': token_info
                }
                self.logger.info(f"✅ Initialized {token_key} contract: {contract_address}")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize {token_key} contract: {e}")
    
    def _resolve_wallet_addresses(self):
        """Разрешение ENS доменов в Ethereum адреса"""
        self.logger.info("🔍 Resolving wallet addresses (including ENS domains)...")
        
        resolved_addresses = get_resolved_wallet_addresses(self.w3)
        
        if resolved_addresses:
            self.monitored_addresses = [addr.lower() for addr in resolved_addresses]
            self.logger.info(f"✅ Resolved {len(self.monitored_addresses)} wallet addresses for monitoring")
            
            # Показываем статистику
            ens_count = len([w for w in MONITORED_WALLETS if is_ens_domain(w)])
            eth_count = len(MONITORED_WALLETS) - ens_count
            self.logger.info(f"📊 Wallets: {ens_count} ENS domains + {eth_count} ETH addresses")
            
            # Показываем примеры разрешенных адресов
            for i, addr in enumerate(self.monitored_addresses[:5]):
                self.logger.info(f"   📍 {i+1}. {addr}")
            if len(self.monitored_addresses) > 5:
                self.logger.info(f"   ... and {len(self.monitored_addresses) - 5} more addresses")
        else:
            self.logger.warning("⚠️  No wallet addresses resolved!")
            self.monitored_addresses = []
    
    async def _update_token_prices(self):
        """Обновление кэша цен токенов"""
        current_time = time.time()
        if current_time - self.last_price_update < 300:  # 5 минут
            return
        
        try:
            self.logger.info("💰 Updating token prices...")
            
            # Получаем цену BIO токена
            bio_price = get_bio_token_price('ethereum')
            if bio_price:
                self.price_cache['BIO'] = bio_price
                self.price_cache['vBIO'] = bio_price  # Предполагаем что vBIO = BIO
                self.logger.info(f"💰 Updated BIO price: ${format_price(bio_price)}")
            
            self.last_price_update = current_time
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update token prices: {e}")
    
    def _calculate_usd_value(self, token_symbol: str, token_amount: float) -> float:
        """Расчет USD стоимости токенов"""
        if token_symbol in self.price_cache:
            return token_amount * self.price_cache[token_symbol]
        return 0.0
    
    async def _check_whale_transaction(self, token_key: str, tx_hash: str, from_address: str, 
                                     to_address: str, amount_raw: int) -> bool:
        """Проверка транзакции на соответствие whale критериям"""
        try:
            token_info = BIO_TOKENS[token_key]
            decimals = token_info['decimals']
            token_amount = amount_raw / (10 ** decimals)
            
            # Проверяем пороговые значения
            meets_token_threshold = token_amount >= WHALE_THRESHOLDS['token_amount']
            
            usd_value = self._calculate_usd_value(token_info['symbol'], token_amount)
            meets_usd_threshold = usd_value >= WHALE_THRESHOLDS['usd_amount']
            
            if meets_token_threshold or meets_usd_threshold:
                self.logger.info(f"🐋 WHALE TRANSACTION DETECTED!")
                self.logger.info(f"   Token: {token_info['symbol']}")
                self.logger.info(f"   Amount: {token_amount:,.2f} tokens")
                self.logger.info(f"   USD Value: ${usd_value:,.2f}")
                self.logger.info(f"   From: {from_address}")
                self.logger.info(f"   To: {to_address}")
                self.logger.info(f"   TX: {tx_hash}")
                
                # Сохраняем в базу данных
                await self._save_whale_transaction(
                    tx_hash, token_key, from_address, to_address, 
                    token_amount, usd_value
                )
                
                # Отправляем уведомление
                await self._send_whale_alert(
                    tx_hash, token_info, from_address, to_address,
                    token_amount, usd_value
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error checking whale transaction: {e}")
            return False
    
    async def _save_whale_transaction(self, tx_hash: str, token_key: str, 
                                    from_address: str, to_address: str,
                                    token_amount: float, usd_value: float):
        """Сохранение whale транзакции в базу данных"""
        try:
            # Проверяем дубликаты
            if self.database.is_duplicate_transaction(tx_hash):
                self.logger.debug(f"⚠️ Duplicate whale transaction skipped: {tx_hash}")
                return
            
            # Сохраняем транзакцию
            transaction_data = {
                'transaction_hash': tx_hash,
                'from_address': from_address,
                'to_address': to_address,
                'token_symbol': BIO_TOKENS[token_key]['symbol'],
                'token_amount': token_amount,
                'usd_value': usd_value,
                'transaction_type': 'whale_transfer',
                'timestamp': datetime.now(timezone.utc),
                'block_number': None  # Можно добавить позже
            }
            
            self.database.save_transaction(transaction_data)
            self.logger.info(f"💾 Saved whale transaction to database: {tx_hash[:16]}...")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save whale transaction: {e}")
    
    async def _send_whale_alert(self, tx_hash: str, token_info: Dict, 
                              from_address: str, to_address: str,
                              token_amount: float, usd_value: float):
        """Отправка уведомления о whale транзакции"""
        try:
            # Подготавливаем данные для системы уведомлений
            transaction_data = {
                'tx_hash': tx_hash,
                'timestamp': datetime.now(timezone.utc),
                'dao_name': 'BIO Whale',  # Условное имя для whale транзакций
                'blockchain': 'ethereum',
                'from_address': from_address,
                'to_address': to_address,
                'token_address': token_info['contract_address'],
                'token_symbol': token_info['symbol'],
                'amount': token_amount,
                'amount_usd': usd_value,
                'tx_type': 'outgoing',
                'alert_triggered': True,
                'metadata': {
                    'whale_alert': True,
                    'token_threshold': token_amount >= WHALE_THRESHOLDS['token_amount'],
                    'usd_threshold': usd_value >= WHALE_THRESHOLDS['usd_amount'],
                    'etherscan_url': f"https://etherscan.io/tx/{tx_hash}",
                    'contract_address': token_info['contract_address']
                }
            }
            
            # Отправляем через систему уведомлений
            if self.notification_system:
                success = await self.notification_system.send_transaction_alert(transaction_data)
                
                if success:
                    self.logger.info(f"📨 Whale alert sent successfully to Telegram")
                else:
                    self.logger.warning(f"❌ Failed to send whale alert to Telegram")
            else:
                self.logger.debug("📤 Notification system not available - alert not sent")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send whale alert: {e}")
    
    async def _scan_token_transfers(self, token_key: str, from_block: int, to_block: int):
        """Сканирование трансферов конкретного токена"""
        try:
            self.logger.info(f"🔍 Starting {token_key} scan from block {from_block} to {to_block}")
            
            token_data = self.token_contracts[token_key]
            contract = token_data['contract']
            
            # Ограничиваем диапазон блоков для избежания timeout
            max_block_range = 100
            if to_block - from_block > max_block_range:
                to_block = from_block + max_block_range
                self.logger.warning(f"⚠️ Limiting block range to {max_block_range} blocks: {from_block}-{to_block}")
            
            self.logger.info(f"📡 Creating Transfer filter for {token_key}...")
            
            # Получаем события Transfer с timeout
            try:
                transfer_filter = contract.events.Transfer.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block
                )
                
                self.logger.info(f"🔍 Getting Transfer events for {token_key}...")
                events = transfer_filter.get_all_entries()
                self.logger.info(f"📊 Found {len(events)} Transfer events for {token_key}")
                
            except Exception as filter_error:
                self.logger.error(f"❌ Error creating/getting filter for {token_key}: {filter_error}")
                return
            
            whale_count = 0
            processed_count = 0
            
            for event in events:
                try:
                    processed_count += 1
                    from_address = event['args']['from']
                    to_address = event['args']['to']
                    amount = event['args']['value']
                    tx_hash = event['transactionHash'].hex()
                    
                    # Проверяем только исходящие транзакции от отслеживаемых кошельков
                    if from_address.lower() in self.monitored_addresses:
                        self.logger.debug(f"🎯 Checking potential whale tx from monitored wallet: {from_address[:10]}...")
                        is_whale = await self._check_whale_transaction(
                            token_key, tx_hash, from_address, to_address, amount
                        )
                        if is_whale:
                            whale_count += 1
                            self.logger.info(f"🐋 Whale transaction detected! #{whale_count}")
                            
                except Exception as event_error:
                    self.logger.error(f"❌ Error processing event {processed_count}: {event_error}")
                    continue
            
            self.logger.info(f"✅ {token_key} scan completed: {processed_count} events processed, {whale_count} whales found")
            
            if whale_count > 0:
                self.logger.info(f"🐋 Found {whale_count} whale transactions for {token_key}")
                
        except Exception as e:
            self.logger.error(f"❌ Error scanning {token_key} transfers: {e}")
            import traceback
            self.logger.error(f"Scan error traceback: {traceback.format_exc()}")
    
    async def run_whale_monitoring_cycle(self):
        """Запуск одного цикла мониторинга whale транзакций"""
        try:
            if not self.monitored_addresses:
                self.logger.warning("⚠️ No wallets configured for monitoring")
                return
            
            self.logger.info("🐋 Starting whale monitoring cycle...")
            
            # Обновляем цены токенов
            try:
                self.logger.info("💰 Updating token prices...")
                await self._update_token_prices()
                self.logger.info("✅ Token prices updated successfully")
            except Exception as price_error:
                self.logger.error(f"❌ Failed to update token prices: {price_error}")
                # Продолжаем работу даже без актуальных цен
            
            # Получаем текущий блок
            try:
                current_block = self.w3.eth.block_number
                lookback_blocks = MONITORING_CONFIG['blocks_lookback']
                from_block = max(1, current_block - lookback_blocks)
                
                self.logger.info(f"🔍 Current block: {current_block}, scanning from {from_block}")
                
            except Exception as block_error:
                self.logger.error(f"❌ Failed to get current block: {block_error}")
                return
            
            # Сканируем каждый токен
            tokens_scanned = 0
            total_tokens = len(self.token_contracts.keys())
            
            for token_key in self.token_contracts.keys():
                try:
                    tokens_scanned += 1
                    self.logger.info(f"🔍 Scanning {token_key} transfers... ({tokens_scanned}/{total_tokens})")
                    await self._scan_token_transfers(token_key, from_block, current_block)
                    self.logger.info(f"✅ {token_key} scan completed")
                    
                except Exception as token_error:
                    self.logger.error(f"❌ Failed to scan {token_key}: {token_error}")
                    continue  # Продолжаем с следующим токеном
            
            self.logger.info(f"✅ Whale monitoring cycle completed successfully! Scanned {tokens_scanned}/{total_tokens} tokens")
            
        except Exception as e:
            self.logger.error(f"❌ Critical error in whale monitoring cycle: {e}")
            import traceback
            self.logger.error(f"Cycle error traceback: {traceback.format_exc()}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Получение статистики мониторинга"""
        return {
            'monitored_wallets': len(self.monitored_addresses),
            'monitored_tokens': len(self.token_contracts),
            'token_threshold': WHALE_THRESHOLDS['token_amount'],
            'usd_threshold': WHALE_THRESHOLDS['usd_amount'],
            'check_interval': MONITORING_CONFIG['check_interval'],
            'price_cache_age': time.time() - self.last_price_update if self.last_price_update else 0
        } 