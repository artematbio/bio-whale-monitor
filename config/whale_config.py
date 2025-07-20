#!/usr/bin/env python3
"""
BIO Whale Monitor Configuration
Конфигурация для мониторинга крупных исходящих транзакций BIO и vBIO токенов
"""

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

# Кошельки для мониторинга (будут добавлены пользователем)
MONITORED_WALLETS = [
    # Добавить адреса кошельков для мониторинга
    # Пример:
    # "0x1234567890123456789012345678901234567890",
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
    
    print(f"\n👛 MONITORED WALLETS:")
    if MONITORED_WALLETS:
        for i, wallet in enumerate(MONITORED_WALLETS, 1):
            print(f"  {i}. {wallet}")
    else:
        print("  ⚠️  No wallets configured yet")
    
    print(f"\n⚙️  MONITORING SETTINGS:")
    print(f"  • Check Interval: {MONITORING_CONFIG['check_interval']} seconds")
    print(f"  • Blocks Lookback: {MONITORING_CONFIG['blocks_lookback']}")
    print(f"  • Retry Attempts: {MONITORING_CONFIG['retry_attempts']}")
    
    print("="*80)

def validate_wallet_address(address: str) -> bool:
    """Валидация Ethereum адреса"""
    if not address.startswith('0x'):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, 16)
        return True
    except ValueError:
        return False

def add_monitored_wallet(address: str) -> bool:
    """Добавляет кошелек в список мониторинга"""
    if validate_wallet_address(address):
        if address.lower() not in [w.lower() for w in MONITORED_WALLETS]:
            MONITORED_WALLETS.append(address)
            return True
    return False 