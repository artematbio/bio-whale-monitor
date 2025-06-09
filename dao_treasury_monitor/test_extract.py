#!/usr/bin/env python3
from read_excel import extract_pool_address

# Тестовые URL из данных
test_urls = [
    'https://dexscreener.com/ethereum/0xcbcc3cbad991ec59204be2963b4a87951e4d292b',
    'https://dexscreener.com/ethereum/0x2dc8fbafc10da100f2f12807b93cbb3e5ff7e6b0',
    'https://dexscreener.com/ethereum/0x94dd312f6cb52c870aacfeeb8bf5e4e28f6952ff',
    'https://dexscreener.com/ethereum/0x61847189477150832d658d8f34f84c603ac269af',
    'https://dexscreener.com/ethereum/0x840faba6f38e28e1494f186990f0f17cb2c7bcac',
    'https://dexscreener.com/ethereum/0x4384273ccd97a503448ca46b3fd1da31689eb2ef',
    'https://dexscreener.com/ethereum/0x6fcee8a45384aec61fdee3fbdd871a338d8ea44c',
    'https://dexscreener.com/ethereum/0x6f4fe0a4033000101c460a93b23c0694b36972c40c9e11d04f7cf8e0aab9c070',
    'https://dexscreener.com/ethereum/0xedc5d54b823873f3bb143a06a5ef2d003c29a933',
    'https://dexscreener.com/ethereum/0x4830570554606cbc37478ab773fde991261fd99c',
    'https://dexscreener.com/ethereum/0x921285db9e2565f9c937e3a5243270aa0002c71a42630a893687023a1a24f62b',
    'https://raydium.io/liquidity-pools/?token=9qU3LmwKJKT2DJeGPihyTP2jc6pC7ij3hPFeyJVzuksN'
]

print("=== TESTING POOL ADDRESS EXTRACTION ===")
for i, url in enumerate(test_urls, 1):
    print(f"\n{i}. URL: {url}")
    extracted = extract_pool_address(url)
    print(f"   Extracted: {extracted}")
    print(f"   Length: {len(extracted) if extracted else 0}") 