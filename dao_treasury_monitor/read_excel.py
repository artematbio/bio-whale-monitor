#!/usr/bin/env python3
import pandas as pd
import re
from urllib.parse import urlparse, parse_qs

def extract_pool_address(url):
    """Извлекает адрес пула из URL"""
    if not url or pd.isna(url):
        return None
    
    url = str(url).strip()
    
    # DexScreener URLs - адрес в конце URL
    if 'dexscreener.com' in url:
        # Сначала пробуем стандартный Ethereum адрес (0x + 40 hex символов)
        match = re.search(r'/0x([0-9a-fA-F]{40})$', url)
        if match:
            return f"0x{match.group(1)}"
        
        # Для очень длинных адресов (больше 40 символов, без 0x)
        match = re.search(r'/([0-9a-fA-F]{60,})$', url)
        if match:
            return match.group(1)
        
        # Для длинных адресов с 0x
        match = re.search(r'/(0x[0-9a-fA-F]{60,})$', url)
        if match:
            return match.group(1)
    
    # Raydium URLs - token параметр
    elif 'raydium.io' in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if 'token' in params:
            return params['token'][0]
    
    return None

def read_dao_data():
    """Читает Excel файл с данными о DAO для мониторинга"""
    try:
        df = pd.read_excel('BIO DAOs monitoring.xlsx')
        
        print("=== COLUMNS ===")
        print(list(df.columns))
        
        print(f"\n=== SHAPE: {df.shape} ===")
        
        # Обрабатываем данные и извлекаем адреса пулов
        dao_configs = []
        clean_df = df.dropna(how='all')
        
        for i, row in clean_df.iterrows():
            row_data = {}
            for col in df.columns:
                if pd.notna(row[col]) and str(row[col]).strip():
                    row_data[col] = str(row[col]).strip()
            
            if row_data and 'DAO' in row_data:  # Только строки с именем DAO
                dao_config = {
                    'name': row_data.get('DAO', ''),
                    'token_symbol': row_data.get('Token', ''),
                    'token_address': row_data.get('Token address', ''),
                    'treasury_address': row_data.get('Treasury', ''),
                    'deployer_address': row_data.get('Deployer', ''),
                    'eth_pool_url': row_data.get('/ETH pool', ''),
                    'bio_pool_url': row_data.get('/BIO pool', ''),
                }
                
                # Извлекаем адреса пулов из URL
                if dao_config['eth_pool_url']:
                    dao_config['eth_pool_address'] = extract_pool_address(dao_config['eth_pool_url'])
                
                if dao_config['bio_pool_url']:
                    dao_config['bio_pool_address'] = extract_pool_address(dao_config['bio_pool_url'])
                
                # Определяем blockchain по формату адреса
                token_addr = dao_config['token_address']
                if token_addr:
                    if token_addr.startswith('0x') and len(token_addr) == 42:
                        dao_config['blockchain'] = 'ethereum'
                    elif len(token_addr) > 32 and not token_addr.startswith('0x'):
                        dao_config['blockchain'] = 'solana'
                    else:
                        dao_config['blockchain'] = 'unknown'
                
                dao_configs.append(dao_config)
        
        print("\n=== PARSED DAO CONFIGURATIONS ===")
        for i, config in enumerate(dao_configs, 1):
            print(f"\n{i}. {config['name']} ({config.get('blockchain', 'unknown')})")
            print(f"   Token: {config['token_symbol']} - {config['token_address']}")
            print(f"   Treasury: {config['treasury_address']}")
            print(f"   Deployer: {config['deployer_address']}")
            
            if config.get('eth_pool_address'):
                print(f"   ETH Pool: {config['eth_pool_address']} ({config['eth_pool_url']})")
            
            if config.get('bio_pool_address'):
                print(f"   BIO Pool: {config['bio_pool_address']} ({config['bio_pool_url']})")
        
        print(f"\n=== SUMMARY ===")
        print(f"Total DAOs: {len(dao_configs)}")
        
        ethereum_daos = [d for d in dao_configs if d.get('blockchain') == 'ethereum']
        solana_daos = [d for d in dao_configs if d.get('blockchain') == 'solana']
        
        print(f"Ethereum DAOs: {len(ethereum_daos)}")
        print(f"Solana DAOs: {len(solana_daos)}")
        
        print(f"\nBIO Token Addresses:")
        print(f"  Ethereum: 0xcb1592591996765Ec0eFc1f92599A19767ee5ffA")
        print(f"  Solana: bioJ9JTqW62MLz7UKHU69gtKhPpGi1BQhccj2kmSvUJ")
        
        # Возвращаем структурированные данные
        return {
            'dao_configs': dao_configs,
            'ethereum_daos': ethereum_daos,
            'solana_daos': solana_daos,
            'raw_df': clean_df
        }
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None

if __name__ == "__main__":
    result = read_dao_data()
    
    # Дополнительный анализ для конфигурации мониторинга
    if result:
        print(f"\n=== MONITORING REQUIREMENTS ===")
        
        all_treasury_addresses = []
        all_token_addresses = []
        all_pool_addresses = []
        
        for dao in result['dao_configs']:
            if dao['treasury_address']:
                all_treasury_addresses.append(dao['treasury_address'])
            
            if dao['token_address']:
                all_token_addresses.append(dao['token_address'])
            
            if dao.get('eth_pool_address'):
                all_pool_addresses.append(dao['eth_pool_address'])
            
            if dao.get('bio_pool_address'):
                all_pool_addresses.append(dao['bio_pool_address'])
        
        print(f"\nTreasury addresses to monitor: {len(all_treasury_addresses)}")
        for addr in all_treasury_addresses:
            print(f"  {addr}")
        
        print(f"\nToken addresses to monitor: {len(all_token_addresses)}")
        for addr in all_token_addresses:
            print(f"  {addr}")
        
        print(f"\nPool addresses to monitor: {len(all_pool_addresses)}")
        for addr in all_pool_addresses:
            if addr:
                print(f"  {addr}") 