#!/usr/bin/env python3
"""
Конфигурация DAO для мониторинга treasury транзакций
Основано на данных из "BIO DAOs monitoring.xlsx"
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

@dataclass
class DAOConfig:
    """Конфигурация DAO для мониторинга"""
    name: str
    token_symbol: str
    token_address: str
    treasury_address: str
    deployer_address: str
    blockchain: str  # 'ethereum' or 'solana'
    
    # Pool информация
    eth_pool_address: Optional[str] = None
    bio_pool_address: Optional[str] = None
    pools: Optional[List[str]] = None  # Для Solana множественных пулов
    
    # Настройки мониторинга
    alert_threshold_usd: Decimal = Decimal("10000")
    monitor_enabled: bool = True

# === BIO TOKEN ADDRESSES ===
BIO_TOKEN_ETHEREUM = "0xcb1592591996765Ec0eFc1f92599A19767ee5ffA"
BIO_TOKEN_SOLANA = "bioJ9JTqW62MLz7UKHU69gtKhPpGi1BQhccj2kmSvUJ"

# === ETHEREUM DAOs (BIO Protocol ecosystem) ===

VITA_DAO = DAOConfig(
    name="VitaDAO",
    token_symbol="VITA",
    token_address="0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321",
    treasury_address="0x03043470A266Cf0Cc85Ca2050F4A66C3F4bfD097",
    deployer_address="0x03043470A266Cf0Cc85Ca2050F4A66C3F4bfD097",
    blockchain="ethereum",
    eth_pool_address="0xc2f2faf46e19cd59b094c92debd5b7b6b6b9aa9c",
    bio_pool_address="0xe8dABB3A6dFE04fb58A6eCf6B8e0B15e5A7ec4F2"
)

HAIR_DAO = DAOConfig(
    name="HairDAO",
    token_symbol="HAIR",
    token_address="0x9c9A3A321ba30DE1b9eFF020e01C38c66c6F7F00",
    treasury_address="0x1e2Df5A1D25b2B31b4226f58c1E1b37e6B3E20a5",
    deployer_address="0x87C5a56EE04C66ab4F67d9Aa1CD7b5cd1c3DA1A2",
    blockchain="ethereum",
    eth_pool_address="0xb73c27b5cecc3e49b6db66c8e5fff3a6de738e2a"
)

VALLEY_DAO = DAOConfig(
    name="Valley DAO",
    token_symbol="GROW", 
    token_address="0x761A3557184cbC07b7493da0661c41177b2f97fA",
    treasury_address="0xD920E60b798A2F5a8332799d8a23075c9E77d5F8",
    deployer_address="0x487707AeDAfE5Da0A4CF8151aB77ed114fa0104E",
    blockchain="ethereum",
    eth_pool_address="0x61847189477150832d658d8f34f84c603ac269af"
)

CEREBRUM_DAO = DAOConfig(
    name="Cerebrum DAO",
    token_symbol="NEURON",
    token_address="0xab814ce69E15F6B9660A3B184c0B0C97B9394A6b", 
    treasury_address="0xb35d6796366B93188AD5a01F60C0Ba45f1BDf11d",
    deployer_address="0x15af6D6C05FD6308196750E68c73bF11a2b5d1A8",
    blockchain="ethereum",
    eth_pool_address="0x840faba6f38e28e1494f186990f0f17cb2c7bcac",
    bio_pool_address="0x4384273ccd97a503448ca46b3fd1da31689eb2ef"
)

CRYO_DAO = DAOConfig(
    name="CryoDAO",
    token_symbol="CRYO",
    token_address="0xf4308b0263723b121056938c2172868E408079D0",
    treasury_address="0xcfaB782fc6DEE9F381f29586aD25BbE6D8F84c7a",
    deployer_address="0xc301C38133B16590Cee4fBe66AaaCDD3B1f3BB29",
    blockchain="ethereum", 
    eth_pool_address="0x6fcee8a45384aec61fdee3fbdd871a338d8ea44c",
    bio_pool_address="0x6f4fe0a4033000101c460a93b23c0694b36972c40c9e11d04f7cf8e0aab9c070"
)

PSY_DAO = DAOConfig(
    name="PsyDAO",
    token_symbol="PSY",
    token_address="0x2196B84EaCe74867b73fb003AfF93C11FcE1D47A",
    treasury_address="0xB253a1Ab24B612C2AF37f8fC935b40c7304650e5",
    deployer_address="0xC3aC5Ef1A15c40241233C722FE322D83B010e445",
    blockchain="ethereum",
    eth_pool_address="0xedc5d54b823873f3bb143a06a5ef2d003c29a933"
)

QUANTUM_BIO_DAO = DAOConfig(
    name="Quantum Biology",
    token_symbol="QBIO", 
    token_address="0x3E6A1b21bd267677Fa49BE6425aEbe2fc0f89bDE",
    treasury_address="0xDF0061710a2a70b6195266B3D618310488E1FE05",
    deployer_address="0x9e67aDFFdfacA157efbC1F0A1785D4D873C20E22",
    blockchain="ethereum",
    eth_pool_address="0x4830570554606cbc37478ab773fde991261fd99c",
    bio_pool_address="0x921285db9e2565f9c937e3a5243270aa0002c71a42630a893687023a1a24f62b"
)

# === SOLANA DAOs (BIO Protocol ecosystem) ===

CURETOPIA_DAO = DAOConfig(
    name="Curetopia",
    token_symbol="CURES",
    token_address="9qU3LmwKJKT2DJeGPihyTP2jc6pC7ij3hPFeyJVzuksN",
    treasury_address="GnJ7vjun5sgt8is79LHAwFf6vPk47hncFPWNfeuYMjVP", 
    deployer_address="58jN4WpSz4Zs11VyeLtJs3TuyMEmooTNrQ3u5AphJfNT",
    blockchain="solana",
    pools=["DojNuRx9Ncky7BbWRfsLmJg2oYb8qsYD344XufUHAjbJ"]  # BIO/CURES pool
)

SPINE_DAO = DAOConfig(
    name="SpineDAO",
    token_symbol="SPINE",
    token_address="spinezMPKxkBpf4Q9xET2587fehM3LuKe4xoAoXtSjR",
    treasury_address="9yrQ6MJLA3HwikqftQVgR4GGZx4X9kFmCdJsDUJGdttM",
    deployer_address="",
    blockchain="solana",
    pools=[
        "CkDV9Eko3KijeRpadFyJTSi4fiBbCT9d3Vdp9JhsUioM",  # SOL/SPINE pool
        "5LZawn1Pqv8Jd96nq5GPVZAz9a7jZWFD66A5JvUodRNL"   # BIO/SPINE pool
    ]
)

MYCO_DAO_1 = DAOConfig(
    name="MYCO DAO (Treasury 1)",
    token_symbol="MYCO",
    token_address="EzYEwn4R5tNkNGw4K2a5a58MJFQESdf1r4UJrV7cpUF3",
    treasury_address="GFHPPeRYW1DAjubnPm5VWGHE5dAGTxTyAZGJs1cFF9fi",
    deployer_address="",
    blockchain="solana",
    pools=[
        "FgCQoL7tcC1nkNazV5onEgWbm9UJ9nbzqo9rZCYm6Yi4",  # MYCO pool 1
        "HhtxoFCY7uxQKBP1AHVXhCQ3jYtRWL3n1CwBKcfoun5Q"   # MYCO pool 2
    ]
)

MYCO_DAO_2 = DAOConfig(
    name="MYCO DAO (Treasury 2)", 
    token_symbol="MYCO",
    token_address="EzYEwn4R5tNkNGw4K2a5a58MJFQESdf1r4UJrV7cpUF3",
    treasury_address="GTuVLSN4cKvrWnWFbyyQX6VW14SLhfu7sjM4MrzFoj3s",
    deployer_address="",
    blockchain="solana",
    pools=[
        "FgCQoL7tcC1nkNazV5onEgWbm9UJ9nbzqo9rZCYm6Yi4",  # MYCO pool 1
        "HhtxoFCY7uxQKBP1AHVXhCQ3jYtRWL3n1CwBKcfoun5Q"   # MYCO pool 2
    ]
)

# === СПИСОК ВСЕХ DAO ДЛЯ МОНИТОРИНГА ===
ALL_DAOS = [
    VITA_DAO,
    HAIR_DAO, 
    VALLEY_DAO,
    CEREBRUM_DAO,
    CRYO_DAO,
    PSY_DAO,
    QUANTUM_BIO_DAO,
    CURETOPIA_DAO,
    SPINE_DAO,
    MYCO_DAO_1,
    MYCO_DAO_2
]

# === РАЗДЕЛЕНИЕ ПО BLOCKCHAIN ===
ETHEREUM_DAOS = [dao for dao in ALL_DAOS if dao.blockchain == "ethereum"]
SOLANA_DAOS = [dao for dao in ALL_DAOS if dao.blockchain == "solana"]

# === СВОДНЫЕ ДАННЫЕ ДЛЯ МОНИТОРИНГА ===

def get_all_treasury_addresses() -> List[str]:
    """Возвращает все treasury адреса для мониторинга"""
    return [dao.treasury_address for dao in ALL_DAOS]

def get_all_token_addresses() -> List[str]:
    """Возвращает все токен адреса для мониторинга"""
    return [dao.token_address for dao in ALL_DAOS]

def get_all_pool_addresses() -> List[str]:
    """Возвращает все адреса пулов для мониторинга"""
    pool_addresses = []
    for dao in ALL_DAOS:
        if dao.eth_pool_address:
            pool_addresses.append(dao.eth_pool_address)
        if dao.bio_pool_address:
            pool_addresses.append(dao.bio_pool_address)
        if dao.pools:
            pool_addresses.extend(dao.pools)
    return pool_addresses

def get_ethereum_addresses() -> dict:
    """Возвращает все Ethereum адреса"""
    return {
        'treasuries': [dao.treasury_address for dao in ETHEREUM_DAOS],
        'tokens': [dao.token_address for dao in ETHEREUM_DAOS],
        'pools': [addr for dao in ETHEREUM_DAOS for addr in [dao.eth_pool_address, dao.bio_pool_address] if addr]
    }

def get_solana_addresses() -> dict:
    """Возвращает все Solana адреса"""
    pools = []
    for dao in SOLANA_DAOS:
        if dao.pools:
            pools.extend(dao.pools)
        if dao.eth_pool_address:
            pools.append(dao.eth_pool_address)
        if dao.bio_pool_address:
            pools.append(dao.bio_pool_address)
    
    return {
        'treasuries': [dao.treasury_address for dao in SOLANA_DAOS],
        'tokens': [dao.token_address for dao in SOLANA_DAOS], 
        'pools': pools
    }

def get_dao_by_treasury_address(treasury_address: str) -> Optional[DAOConfig]:
    """Находит DAO по treasury адресу"""
    for dao in ALL_DAOS:
        if dao.treasury_address.lower() == treasury_address.lower():
            return dao
    return None

def get_dao_by_token_address(token_address: str) -> Optional[DAOConfig]:
    """Находит DAO по токен адресу"""
    for dao in ALL_DAOS:
        if dao.token_address.lower() == token_address.lower():
            return dao
    return None

def get_dao_by_pool_address(pool_address: str) -> Optional[DAOConfig]:
    """Находит DAO по pool адресу"""
    pool_address_lower = pool_address.lower()
    for dao in ALL_DAOS:
        if dao.eth_pool_address and dao.eth_pool_address.lower() == pool_address_lower:
            return dao
        if dao.bio_pool_address and dao.bio_pool_address.lower() == pool_address_lower:
            return dao
        if dao.pools:
            for pool in dao.pools:
                if pool.lower() == pool_address_lower:
                    return dao
    return None

# === SUMMARY STATISTICS ===
def print_monitoring_summary():
    """Выводит сводную статистику мониторинга"""
    print("=== DAO TREASURY MONITOR CONFIGURATION ===")
    print(f"Total DAOs: {len(ALL_DAOS)}")
    print(f"Ethereum DAOs: {len(ETHEREUM_DAOS)}")
    print(f"Solana DAOs: {len(SOLANA_DAOS)}")
    print(f"Treasury addresses: {len(get_all_treasury_addresses())}")
    print(f"Token addresses: {len(get_all_token_addresses())}")
    print(f"Pool addresses: {len(get_all_pool_addresses())}")
    
    print(f"\nBIO Token addresses:")
    print(f"  Ethereum: {BIO_TOKEN_ETHEREUM}")
    print(f"  Solana: {BIO_TOKEN_SOLANA}")
    
    print(f"\nAlert threshold: ${ALL_DAOS[0].alert_threshold_usd:,}")

if __name__ == "__main__":
    print_monitoring_summary()
    
    print(f"\n=== DAO DETAILS ===")
    for i, dao in enumerate(ALL_DAOS, 1):
        print(f"\n{i}. {dao.name} ({dao.blockchain})")
        print(f"   Token: {dao.token_symbol} - {dao.token_address}")
        print(f"   Treasury: {dao.treasury_address}")
        if dao.eth_pool_address:
            print(f"   ETH Pool: {dao.eth_pool_address}")
        if dao.bio_pool_address:
            print(f"   BIO Pool: {dao.bio_pool_address}")
        if dao.pools:
            print(f"   Pools: {len(dao.pools)} pool(s)")
            for j, pool in enumerate(dao.pools, 1):
                print(f"     {j}. {pool}") 