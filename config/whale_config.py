#!/usr/bin/env python3
"""
BIO Whale Monitor Configuration
Конфигурация для мониторинга крупных исходящих транзакций BIO и vBIO токенов
"""

from typing import List

# BIO и vBIO токены на Ethereum
BIO_TOKENS = {
    "BIO": {
        "contract_address": "0xcb1592591996765Ec0eFc1f92599A19767ee5ffA",  # BIO token contract
        "symbol": "BIO",
        "decimals": 18,
        "name": "BIO Protocol"
    },
    "vBIO": {
        "contract_address": "0x2141B47A1C7De6df073d23ff94F04d9fd2aaA9b3",  # vBIO contract (нужно уточнить)
        "symbol": "vBIO", 
        "decimals": 18,
        "name": "Voting BIO"
    }
}

# Пороговые значения для алертов
WHALE_THRESHOLDS = {
    "token_amount": 1_000_000,  # 1 миллион токенов
    "usd_amount": 100_000,      # $100,000 USD
}

# Кошельки для мониторинга (включая ENS домены)
MONITORED_WALLETS = [
    # ENS домены (будут автоматически разрешены в адреса)
    "balajis.eth",
    "katelynd.eth", 
    "commonshare.eth",
    "qiao.eth",
    "toddwhite.eth",
    
    # Ethereum адреса
    "0xEe05A01deb017653e93db88D48B30aEb0dA70B5E",
    "0xa4598EB5B7f8d43e1DF8C3471E7a0f6B413d7c17",
    "0xC84eAD262729f86c9fB18c1A30c3E6F32C1ed80E",
    "0x5d76A92b7cB9E1A81B8eb8c16468F1155B2f64f4",
    "0x5E79A38034862733788EEfdC3FfEDB094444c482",
    "0x76aa796Fc7d8f55772240B4D25b50D90C478c2A9",
    "0x71028407594d438A5f718972228538d0002c6D7f",
    "0x3ac2c9165321116f8cb10b372cab8410d451a94b",
    "0x1118BA8E50Aa2475DC88aa2711db4fb23cf0cE60",
    "0xc590266b8639a187ae9eC16ADBB0aE14cFAaeC52",
    "0x8daF33E2B5812D16e02Da7B47761c910313E1CaF",
    "0x1741cDc1381fe9643e84F90071D6347965929908",
    "0x032D132DB8DE289DA579882F492412BC670F9FCB",
    "0xa67EcE9340Dd55168B50080276be3eB94925C587",
    "0xFE34b009f5ECB373dF71dc18394E478E281b4117",
    "0x8E57bC446f76B2054089CC5c8fA6F0F5B72fC59a",
    "0x6540808a6C6Aa88f33E6b42156A2dB994c49D202",
    "0x09D34bF08fdC34A8cFD0B367575036B5D8bE66D6",
    "0xC18407e878e41EF03E8c55acc64106d93BE3691b",
    "0x6161cF65032C06fdBED20E37588ea7760d8e376B",
    "0xB10B5568d516a6121A848b86A0640115827430b1",
    "0xbc6a93cc98c8bbb25f3f8da098468406a8f99484",
    "0x0601Df345aFE12034E54857583965458947C4bfC",
    "0x64C5029EaA2c985180e604A6Cc6eAe607D12899F",
    "0x6B2699439907DBBC44e7524118169BEE01341A34",
    "0xAd7e1Fb853BE16A8e2Eff932D4bF111cD18F120f",
    "0xB311b148fC9964347546816C8e2f8A23C7e7eAaF",
    "0xa6667F1A0beA0D7B96B47CC1357631842d05E40F",
    "0x0a6a7fecce6d5b2d1b302ca419255f79bb2fa0c1",
    "0x510A150E743e38216630A9833E7108a43194f6c7",
    "0x3Fa21fd164aBA0753c79ca4072429917a9079C22",
    "0x6a89EC93407D769B490ebFd658b8caB34D748aC1",
    "0x8615F13C12c24DFdca0ba32511E2861BE02b93b2",
    "0xD481EE01b8825387d950a812255A240f00DC125F",
    "0xf219BF96B7A5A012a2c9F4c15Bee96cdF8F4D58D",
    "0xE66F38B84E82d36455DdA59af2b59Cb2D32b209f",
    "0xF0e4A659461a1fb29F49f275a59309C2CACf83d7",
    "0x3d03E52023cf0A2117d4a3960356050FA7e87b62",
    "0xfeECDBA833101f66e01E1c1C6E5c99ac4DacE274",
    "0x33c0e5319De60f5609EeB9F037fEfb4f50600216",
    "0xd8d70C810072CbcC72b4939b1fbD932E185Ad931",
    "0x7514654D63e616C81a9Fc0776dd321928Ceb30Db",
    "0x5c4eab70efd03eff220227bcdc051e6932af4c84",
    "0xe67F7FcC2695564a35A9fBdc5b7A35969Dc7Ac1F",
    "0x55420601591b6A4CF14F2cf912aB377898fb9201",
    "0x812cd100e4c4e001a96a7cb3fb2513e93e44940b",
    "0x39D787fdf7384597C7208644dBb6FDa1CcA4eBdf",
    "0x2D81713c58452c92C19b2917e1C770eEcF53Fe41",
    "0x00a33C8379B03085Ad0c0B4F6FB38C63dEBa8475",
    "0x953efb623d893A64E808B2a1607C939f688c8e44",
    "0x6DA18E529a7503150D6fdd1a0156EC23e02009cA",
    "0x87F91943345923039182ab2444b686dBc7c4a200",
    "0x6c1e0C4221ec9d36Cf80cd2B9b6B9B2823e4CB69",
]

# Настройки мониторинга
MONITORING_CONFIG = {
    "check_interval": 30,  # Интервал проверки в секундах
    "blocks_lookback": 5,  # Количество блоков для проверки назад
    "retry_attempts": 3,
    "retry_delay": 5,
}

def print_whale_monitoring_summary():
    """Выводит сводку конфигурации whale мониторинга"""
    print("\n" + "="*80)
    print("🐋 BIO WHALE MONITOR CONFIGURATION")
    print("="*80)
    
    print(f"\n📊 TOKENS TO MONITOR:")
    for token_key, token_info in BIO_TOKENS.items():
        print(f"  • {token_info['name']} ({token_info['symbol']})")
        print(f"    Contract: {token_info['contract_address']}")
        print(f"    Decimals: {token_info['decimals']}")
    
    print(f"\n🚨 ALERT THRESHOLDS:")
    print(f"  • Token Amount: {WHALE_THRESHOLDS['token_amount']:,} tokens")
    print(f"  • USD Value: ${WHALE_THRESHOLDS['usd_amount']:,}")
    
    print(f"\n👛 MONITORED WALLETS ({len(MONITORED_WALLETS)} total):")
    
    # Разделяем ENS домены и обычные адреса
    ens_domains = [w for w in MONITORED_WALLETS if is_ens_domain(w)]
    eth_addresses = [w for w in MONITORED_WALLETS if not is_ens_domain(w)]
    
    if ens_domains:
        print(f"\n  🌐 ENS Domains ({len(ens_domains)}):")
        for i, domain in enumerate(ens_domains, 1):
            print(f"    {i}. {domain}")
    
    if eth_addresses:
        print(f"\n  📍 Ethereum Addresses ({len(eth_addresses)}):")
        for i, addr in enumerate(eth_addresses[:10], 1):  # Показываем первые 10
            print(f"    {i}. {addr}")
        if len(eth_addresses) > 10:
            print(f"    ... and {len(eth_addresses) - 10} more addresses")
    
    print(f"\n⚙️  MONITORING SETTINGS:")
    print(f"  • Check Interval: {MONITORING_CONFIG['check_interval']} seconds")
    print(f"  • Blocks Lookback: {MONITORING_CONFIG['blocks_lookback']}")
    print(f"  • Retry Attempts: {MONITORING_CONFIG['retry_attempts']}")
    
    print("\n💡 NOTES:")
    print("  • ENS domains will be automatically resolved to addresses")
    print("  • Only outgoing transactions from monitored wallets are tracked")
    print("  • Alerts trigger when either token OR USD threshold is exceeded")
    
    print("="*80)

def validate_wallet_address(address: str) -> bool:
    """Валидация Ethereum адреса или ENS домена"""
    # Проверка ENS домена
    if address.endswith('.eth'):
        return len(address) > 4  # Минимум 'a.eth'
    
    # Проверка обычного Ethereum адреса
    if not address.startswith('0x'):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, 16)
        return True
    except ValueError:
        return False

def is_ens_domain(address: str) -> bool:
    """Проверяет, является ли адрес ENS доменом"""
    return address.endswith('.eth')

def resolve_ens_domain(ens_domain: str, web3_instance) -> str:
    """
    Разрешает ENS домен в Ethereum адрес
    
    Args:
        ens_domain: ENS домен (например, 'vitalik.eth')
        web3_instance: Web3 instance с подключенным ENS
    
    Returns:
        Ethereum адрес или пустую строку если не удалось разрешить
    """
    try:
        if not is_ens_domain(ens_domain):
            return ens_domain  # Если это уже адрес, возвращаем как есть
        
        # Разрешаем ENS домен
        resolved_address = web3_instance.ens.address(ens_domain)
        
        if resolved_address:
            return resolved_address
        else:
            return ""
            
    except Exception as e:
        print(f"❌ Failed to resolve ENS domain {ens_domain}: {e}")
        return ""

def get_resolved_wallet_addresses(web3_instance=None) -> List[str]:
    """
    Получает список всех кошельков с разрешенными ENS доменами
    
    Args:
        web3_instance: Web3 instance для разрешения ENS доменов
    
    Returns:
        Список Ethereum адресов (ENS домены разрешены в адреса)
    """
    resolved_addresses = []
    
    for wallet in MONITORED_WALLETS:
        if is_ens_domain(wallet):
            if web3_instance:
                resolved_address = resolve_ens_domain(wallet, web3_instance)
                if resolved_address:
                    resolved_addresses.append(resolved_address.lower())
                else:
                    print(f"⚠️  Failed to resolve ENS domain: {wallet}")
            else:
                print(f"⚠️  Web3 instance required to resolve ENS domain: {wallet}")
        else:
            resolved_addresses.append(wallet.lower())
    
    # Удаляем дубликаты
    return list(set(resolved_addresses))

def add_monitored_wallet(address: str) -> bool:
    """Добавляет кошелек в список мониторинга"""
    if validate_wallet_address(address):
        # Проверяем нет ли уже такого адреса/домена
        existing_addresses = [w.lower() for w in MONITORED_WALLETS]
        if address.lower() not in existing_addresses:
            MONITORED_WALLETS.append(address)
            return True
    return False 