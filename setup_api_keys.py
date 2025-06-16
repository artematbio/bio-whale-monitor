#!/usr/bin/env python3
"""
Интерактивная настройка API ключей для Pool Monitoring
"""

import os
import sys

def print_banner():
    print("🔧 DAO Treasury Monitor - Настройка API ключей")
    print("=" * 50)
    print()

def print_step(step, title):
    print(f"📋 Шаг {step}: {title}")
    print("-" * 30)

def create_env_file():
    """Создает .env файл с пользовательскими ключами"""
    
    print_banner()
    
    # Проверяем существует ли .env файл
    if os.path.exists('.env'):
        answer = input("❓ Файл .env уже существует. Перезаписать? (y/N): ").strip().lower()
        if answer not in ['y', 'yes', 'да']:
            print("❌ Отменено пользователем")
            return False
    
    print_step(1, "Получение BitQuery API ключа")
    print("🏊 BitQuery API (для Solana пулов)")
    print("📝 Инструкция:")
    print("   1. Перейдите на https://ide.bitquery.io/")
    print("   2. Зарегистрируйтесь (бесплатно)")
    print("   3. Выберите Developer план (10,000 поинтов бесплатно)")
    print("   4. Перейдите в Profile → API Keys")
    print("   5. Скопируйте ваш API ключ")
    print()
    
    bitquery_key = input("🔑 Введите BitQuery API ключ (или нажмите Enter чтобы пропустить): ").strip()
    if not bitquery_key:
        bitquery_key = "your_bitquery_api_key_here"
        print("⚠️ BitQuery API ключ не настроен - Solana пулы не будут мониториться")
    else:
        print("✅ BitQuery API ключ сохранен")
    print()
    
    print_step(2, "Получение Helius API ключа")
    print("🚀 Helius API (для Solana RPC)")
    print("📝 Инструкция:")
    print("   1. Перейдите на https://dashboard.helius.dev/signup")
    print("   2. Зарегистрируйтесь (бесплатно)")
    print("   3. Free план (1M кредитов бесплатно)")
    print("   4. В Dashboard перейдите в API Keys")
    print("   5. Скопируйте ваш API ключ")
    print()
    
    helius_key = input("🔑 Введите Helius API ключ (или нажмите Enter чтобы пропустить): ").strip()
    if not helius_key:
        helius_key = "your_helius_api_key_here"
        print("⚠️ Helius API ключ не настроен - Solana RPC будет ограничен")
    else:
        print("✅ Helius API ключ сохранен")
    print()
    
    print_step(3, "Создание .env файла")
    
    # Читаем шаблон
    try:
        with open('env_template.txt', 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print("❌ Файл env_template.txt не найден")
        return False
    
    # Заменяем placeholder'ы
    env_content = template.replace('your_bitquery_api_key_here', bitquery_key)
    env_content = env_content.replace('your_helius_api_key_here', helius_key)
    
    # Сохраняем .env файл
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ Файл .env создан успешно")
    except Exception as e:
        print(f"❌ Ошибка создания .env файла: {e}")
        return False
    
    print()
    print_step(4, "Проверка настроек")
    print("🧪 Теперь вы можете запустить тест:")
    print("   python test_pool_monitoring.py")
    print()
    print("🚀 Или запустить полный мониторинг:")
    print("   python main.py")
    print()
    
    return True

def show_current_config():
    """Показывает текущую конфигурацию"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ python-dotenv не установлен. Установите: pip install python-dotenv")
        return
    
    print_banner()
    print("📊 Текущая конфигурация:")
    print()
    
    # Проверяем API ключи
    bitquery_key = os.getenv('BITQUERY_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat = os.getenv('TELEGRAM_CHAT_ID', '')
    ethereum_rpc = os.getenv('ETHEREUM_RPC_URL', '')
    
    configs = [
        ("BitQuery API", bitquery_key, "Solana пулы"),
        ("Helius API", helius_key, "Solana RPC"),
        ("Telegram Bot", telegram_token, "Уведомления"),
        ("Telegram Chat", telegram_chat, "Уведомления"),
        ("Ethereum RPC", ethereum_rpc, "Ethereum пулы")
    ]
    
    for name, value, purpose in configs:
        if value and value != f'your_{name.lower().replace(" ", "_")}_api_key_here':
            status = "✅ Настроен"
            preview = f"{value[:20]}..." if len(value) > 20 else value
        else:
            status = "❌ Не настроен"
            preview = "Не задан"
        
        print(f"{name:15}: {status:12} | {purpose:20} | {preview}")
    
    print()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_current_config()
    else:
        create_env_file()

if __name__ == "__main__":
    main() 