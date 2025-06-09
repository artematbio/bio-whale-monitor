#!/usr/bin/env python3
"""
Утилиты для получения цен токенов
Использует CoinGecko API для получения текущих цен токенов
"""

import httpx
import logging
import time
from typing import Dict, Optional, Union, List
from decimal import Decimal
import os

logger = logging.getLogger(__name__)

# Константы CoinGecko API (как в pool_analyzer.py)
COINGECKO_ENDPOINT = "https://pro-api.coingecko.com/api/v3/"
COINGECKO_API_KEY = "CG-9MrJcucBMMx5HKnXeVBD8oSb"

class PriceCache:
    """Кэш для цен токенов"""
    
    def __init__(self, ttl: int = 300):  # 5 минут TTL
        self.cache = {}
        self.ttl = ttl
        self.last_update = {}
    
    def get(self, key: str) -> Optional[Decimal]:
        """Получение цены из кэша"""
        if key not in self.cache:
            return None
        
        if time.time() - self.last_update.get(key, 0) > self.ttl:
            # Цена устарела
            del self.cache[key]
            if key in self.last_update:
                del self.last_update[key]
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value: Decimal):
        """Установка цены в кэш"""
        self.cache[key] = value
        self.last_update[key] = time.time()
    
    def clear(self):
        """Очистка кэша"""
        self.cache.clear()
        self.last_update.clear()

# Глобальный кэш цен
price_cache = PriceCache()

def get_coingecko_api_key() -> str:
    """Получение API ключа CoinGecko"""
    return os.getenv('COINGECKO_API_KEY', COINGECKO_API_KEY)

async def get_token_price_coingecko(token_address: str, blockchain: str = 'ethereum', client: httpx.AsyncClient = None) -> Decimal:
    """
    Получение цены токена через CoinGecko API (как в pool_analyzer.py)
    
    Args:
        token_address: Адрес токена
        blockchain: Блокчейн ('ethereum' или 'solana')
        client: httpx.AsyncClient для HTTP запросов
    
    Returns:
        Decimal: Цена токена в USD
    """
    try:
        # Проверяем кэш
        cache_key = f"{blockchain}:{token_address.lower()}"
        cached_price = price_cache.get(cache_key)
        if cached_price is not None:
            logger.debug(f"Using cached price for {token_address}: ${cached_price}")
            return cached_price
        
        # Определяем платформу для CoinGecko
        if blockchain.lower() == 'ethereum':
            platform = 'ethereum'
        elif blockchain.lower() == 'solana':
            platform = 'solana'
        else:
            logger.error(f"Unsupported blockchain: {blockchain}")
            return Decimal('0')
        
        # Запрос к CoinGecko API (как в pool_analyzer.py)
        api_key = get_coingecko_api_key()
        url = f"{COINGECKO_ENDPOINT}simple/token_price/{platform}"
        
        params = {
            'contract_addresses': token_address.lower(),
            'vs_currencies': 'usd'
        }
        
        headers = {}
        if api_key:
            headers["x-cg-pro-api-key"] = api_key
        
        # Создаем временный клиент если не передан
        if client is None:
            async with httpx.AsyncClient(timeout=10.0) as temp_client:
                response = await temp_client.get(url, params=params, headers=headers)
        else:
            response = await client.get(url, params=params, headers=headers)
        
        response.raise_for_status()
        response_data = response.json()
        
        # Извлекаем цену
        token_data = response_data.get(token_address.lower(), {})
        price_usd = token_data.get('usd', 0)
        
        if price_usd > 0:
            price = Decimal(str(price_usd))
            # Сохраняем в кэш
            price_cache.set(cache_key, price)
            logger.debug(f"Fetched price for {token_address}: ${price}")
            return price
        else:
            logger.warning(f"No price data for token {token_address}")
            return Decimal('0')
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("CoinGecko API rate limit exceeded")
        else:
            logger.error(f"CoinGecko API HTTP error: {e.response.status_code} - {e.response.text}")
        return Decimal('0')
    except Exception as e:
        logger.error(f"Error fetching price for {token_address}: {e}")
        return Decimal('0')

async def get_token_prices_geckoterminal(token_addresses: List[str], client: httpx.AsyncClient) -> Dict[str, Decimal]:
    """Fetch token prices from GeckoTerminal API (copied from pool_analyzer.py)"""
    try:
        prices = {}
        
        logger.debug(f"STARTING GeckoTerminal price fetch for {len(token_addresses)} tokens: {token_addresses}")
        
        for token_address in token_addresses:
            logger.info(f"Fetching price from GeckoTerminal for token {token_address}...")
            https_url = f"https://api.geckoterminal.com/api/v2/networks/solana/tokens/{token_address}"
            
            try:
                headers = {"Accept": "application/json"}
                logger.debug(f"GeckoTerminal API request URL: {https_url}")
                response = await client.get(https_url, headers=headers)
                
                logger.debug(f"GeckoTerminal response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.warning(f"GeckoTerminal: Could not fetch price for {token_address}. Status: {response.status_code}")
                    continue
                
                response_data = response.json()
                logger.debug(f"GeckoTerminal raw response: {response_data}")
                
                price_usd = None
                if response_data and "data" in response_data and "attributes" in response_data["data"]:
                    price_usd = response_data["data"]["attributes"].get("price_usd")
                
                if price_usd is not None and price_usd != "":
                    price_decimal = Decimal(str(price_usd))
                    prices[token_address] = price_decimal
                    logger.info(f"GeckoTerminal: Price for {token_address} = {price_usd} USD")
                else:
                    logger.warning(f"GeckoTerminal: Price not found or invalid in response for {token_address}.")
                    
            except httpx.HTTPError as e:
                logger.warning(f"GeckoTerminal: HTTP error for {token_address}: {e}")
            except Exception as e:
                logger.warning(f"GeckoTerminal: Error fetching price for {token_address}: {e}")
        
        logger.debug(f"COMPLETED GeckoTerminal price fetch. Found prices for {len(prices)}/{len(token_addresses)} tokens")
        return prices
    except Exception as e:
        logger.error(f"Error in fetch_token_prices_geckoterminal: {e}")
        return {}

async def get_multiple_token_prices(token_addresses: list, blockchain: str = 'ethereum', client: httpx.AsyncClient = None) -> Dict[str, Decimal]:
    """
    Получение цен нескольких токенов одним запросом (как в pool_analyzer.py)
    
    Args:
        token_addresses: Список адресов токенов
        blockchain: Блокчейн
        client: httpx.AsyncClient для HTTP запросов
    
    Returns:
        Dict: Словарь {адрес_токена: цена}
    """
    results = {}
    
    try:
        # Проверяем кэш для всех токенов
        uncached_tokens = []
        for token_address in token_addresses:
            cache_key = f"{blockchain}:{token_address.lower()}"
            cached_price = price_cache.get(cache_key)
            if cached_price is not None:
                results[token_address] = cached_price
            else:
                uncached_tokens.append(token_address)
        
        if not uncached_tokens:
            logger.debug("All token prices found in cache")
            return results
        
        # Для Solana используем GeckoTerminal как основной источник
        if blockchain.lower() == 'solana':
            logger.info(f"Using GeckoTerminal for Solana tokens: {uncached_tokens}")
            
            # Создаем временный клиент если не передан
            if client is None:
                async with httpx.AsyncClient(timeout=15.0) as temp_client:
                    gecko_prices = await get_token_prices_geckoterminal(uncached_tokens, temp_client)
            else:
                gecko_prices = await get_token_prices_geckoterminal(uncached_tokens, client)
            
            # Обновляем результаты и кэш
            for token_address in uncached_tokens:
                price = gecko_prices.get(token_address, Decimal('0'))
                results[token_address] = price
                
                # Сохраняем в кэш
                cache_key = f"{blockchain}:{token_address.lower()}"
                price_cache.set(cache_key, price)
                
                if price == Decimal('0'):
                    logger.warning(f"No price from GeckoTerminal for {token_address}")
                else:
                    logger.info(f"GeckoTerminal price for {token_address}: ${price}")
        
        # Для Ethereum используем CoinGecko
        elif blockchain.lower() == 'ethereum':
            logger.info(f"Using CoinGecko for Ethereum tokens: {uncached_tokens}")
            
            # Запрос для некэшированных токенов
            api_key = get_coingecko_api_key()
            url = f"{COINGECKO_ENDPOINT}simple/token_price/ethereum"
            
            # CoinGecko может обработать до 100 токенов за раз
            batch_size = 50  # Оставляем запас
            
            for i in range(0, len(uncached_tokens), batch_size):
                batch = uncached_tokens[i:i + batch_size]
                batch_addresses = ','.join([addr.lower() for addr in batch])
                
                params = {
                    'contract_addresses': batch_addresses,
                    'vs_currencies': 'usd'
                }
                
                headers = {}
                if api_key:
                    headers["x-cg-pro-api-key"] = api_key
                
                # Создаем временный клиент если не передан
                if client is None:
                    async with httpx.AsyncClient(timeout=15.0) as temp_client:
                        response = await temp_client.get(url, params=params, headers=headers)
                else:
                    response = await client.get(url, params=params, headers=headers)
                
                response.raise_for_status()
                data = response.json()
                
                for token_address in batch:
                    token_data = data.get(token_address.lower(), {})
                    price_usd = token_data.get('usd', 0)
                    
                    if price_usd > 0:
                        price = Decimal(str(price_usd))
                        results[token_address] = price
                        
                        # Сохраняем в кэш
                        cache_key = f"{blockchain}:{token_address.lower()}"
                        price_cache.set(cache_key, price)
                    else:
                        results[token_address] = Decimal('0')
                        logger.warning(f"No price data for token {token_address}")
                
                # Небольшая задержка между батчами
                if i + batch_size < len(uncached_tokens):
                    await httpx.AsyncClient().aclose()  # Освобождаем соединения
                    time.sleep(0.5)
        
        else:
            logger.error(f"Unsupported blockchain: {blockchain}")
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(f"API rate limit exceeded in batch request for {blockchain}")
        else:
            logger.error(f"API batch HTTP error for {blockchain}: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Error getting multiple token prices for {blockchain}: {e}")
    
    # Заполняем отсутствующие цены нулями
    for token_address in token_addresses:
        if token_address not in results:
            results[token_address] = Decimal('0')
    
    return results

# Синхронные обёрточные функции для обратной совместимости
def get_token_price(token_address: str, blockchain: str = 'ethereum') -> Decimal:
    """
    Синхронная обёртка для получения цены токена
    
    Args:
        token_address: Адрес токена
        blockchain: Блокчейн ('ethereum' или 'solana')
    
    Returns:
        Decimal: Цена токена в USD
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если цикл уже запущен, используем синхронный httpx
            import httpx
            
            if blockchain.lower() == 'solana':
                # Для Solana используем GeckoTerminal
                url = f"https://api.geckoterminal.com/api/v2/networks/solana/tokens/{token_address}"
                headers = {"Accept": "application/json"}
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        price_usd = None
                        if response_data and "data" in response_data and "attributes" in response_data["data"]:
                            price_usd = response_data["data"]["attributes"].get("price_usd")
                        
                        if price_usd is not None and price_usd != "":
                            return Decimal(str(price_usd))
                    
                    logger.warning(f"GeckoTerminal: Could not fetch price for {token_address}")
                    return Decimal('0')
            
            else:
                # Для Ethereum используем CoinGecko
                url = f"{COINGECKO_ENDPOINT}simple/token_price/{blockchain}"
                params = {
                    'contract_addresses': token_address.lower(),
                    'vs_currencies': 'usd'
                }
                headers = {}
                api_key = get_coingecko_api_key()
                if api_key:
                    headers["x-cg-pro-api-key"] = api_key
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    response_data = response.json()
                    
                    token_data = response_data.get(token_address.lower(), {})
                    price_usd = token_data.get('usd', 0)
                    
                    if price_usd > 0:
                        return Decimal(str(price_usd))
                    else:
                        return Decimal('0')
        else:
            # Если цикл не запущен, используем run_until_complete
            if blockchain.lower() == 'solana':
                # Используем GeckoTerminal асинхронно
                return loop.run_until_complete(get_token_price_solana_async(token_address))
            else:
                return loop.run_until_complete(get_token_price_coingecko(token_address, blockchain))
                
    except Exception as e:
        logger.error(f"Error getting token price for {token_address}: {e}")
        return Decimal('0')

async def get_token_price_solana_async(token_address: str) -> Decimal:
    """Асинхронное получение цены Solana токена через GeckoTerminal"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            prices = await get_token_prices_geckoterminal([token_address], client)
            return prices.get(token_address, Decimal('0'))
    except Exception as e:
        logger.error(f"Error getting Solana token price for {token_address}: {e}")
        return Decimal('0')

def calculate_usd_value(token_amount: Union[int, float, Decimal], token_price: Decimal) -> Decimal:
    """
    Расчет USD стоимости токенов
    
    Args:
        token_amount: Количество токенов
        token_price: Цена токена в USD
    
    Returns:
        Decimal: Стоимость в USD
    """
    try:
        if isinstance(token_amount, (int, float)):
            amount = Decimal(str(token_amount))
        else:
            amount = token_amount
        
        return amount * token_price
        
    except Exception as e:
        logger.error(f"Error calculating USD value: {e}")
        return Decimal('0')

def format_price(price: Decimal, decimals: int = 6) -> str:
    """
    Форматирование цены для отображения
    
    Args:
        price: Цена
        decimals: Количество знаков после запятой
    
    Returns:
        str: Отформатированная цена
    """
    try:
        if price == 0:
            return "$0.00"
        
        if price >= 1:
            return f"${price:,.2f}"
        else:
            # Для малых цен показываем больше знаков
            return f"${price:.{decimals}f}".rstrip('0').rstrip('.')
            
    except Exception as e:
        logger.error(f"Error formatting price: {e}")
        return "$0.00"

def get_bio_token_price(blockchain: str = 'ethereum') -> Decimal:
    """
    Получение цены BIO токена
    
    Args:
        blockchain: 'ethereum' или 'solana'
    
    Returns:
        Decimal: Цена BIO токена в USD
    """
    if blockchain.lower() == 'ethereum':
        bio_address = "0xcb1592591996765Ec0eFc1f92599A19767ee5ffA"
    elif blockchain.lower() == 'solana':
        bio_address = "bioJ9JTqW62MLz7UKHU69gtKhPpGi1BQhccj2kmSvUJ"
    else:
        logger.error(f"Unsupported blockchain for BIO token: {blockchain}")
        return Decimal('0')
    
    return get_token_price(bio_address, blockchain)

if __name__ == "__main__":
    # Тестирование утилит для работы с ценами
    logging.basicConfig(level=logging.INFO)
    
    print("=== TESTING PRICE UTILITIES ===")
    
    # Тест получения цены одного токена
    print("\n1. Testing single token price...")
    vita_price = get_token_price("0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321", "ethereum")
    print(f"VITA price: {format_price(vita_price)}")
    
    # Тест получения цены BIO токена
    print("\n2. Testing BIO token price...")
    bio_eth_price = get_bio_token_price("ethereum")
    bio_sol_price = get_bio_token_price("solana")
    print(f"BIO (Ethereum) price: {format_price(bio_eth_price)}")
    print(f"BIO (Solana) price: {format_price(bio_sol_price)}")
    
    # Тест расчета USD стоимости
    print("\n3. Testing USD value calculation...")
    amount = Decimal("1000")
    usd_value = calculate_usd_value(amount, vita_price)
    print(f"1000 VITA = {format_price(usd_value)}")
    
    # Статистика кэша
    print(f"\n4. Cache statistics:")
    print(f"Cached prices: {len(price_cache.cache)}")
    for key, price in price_cache.cache.items():
        print(f"  {key}: {format_price(price)}") 