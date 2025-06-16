# 🔑 Настройка API ключей для Pool Monitoring

## 📋 Необходимые API ключи

### 1. 🏊 BitQuery API (для Solana пулов)
- **URL регистрации**: https://ide.bitquery.io/
- **План**: Developer (БЕСПЛАТНЫЙ)
- **Лимиты**: 10,000 поинтов для тестирования
- **Получение ключа**: Profile → API Keys
- **Назначение**: Мониторинг Solana DEX трейдов

### 2. 🚀 Helius API (для Solana RPC)
- **URL регистрации**: https://dashboard.helius.dev/signup
- **План**: Free (БЕСПЛАТНЫЙ)  
- **Лимиты**: 1M кредитов
- **Получение ключа**: Dashboard → API Keys
- **Назначение**: Solana RPC доступ

## 🔧 Настройка переменных окружения

После получения ключей выполните:

```bash
# 1. Создайте файл .env
cp .env.example .env

# 2. Отредактируйте .env файл и добавьте ваши ключи:
# BITQUERY_API_KEY=ваш_ключ_bitquery
# HELIUS_API_KEY=ваш_ключ_helius
```

## 📝 Пример заполнения .env

```bash
# Pool Monitoring APIs
BITQUERY_API_KEY=BQY_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HELIUS_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Уже настроенные
TELEGRAM_BOT_TOKEN=7132907460:AAGCduLmhc5njQ43C_PMyGfG1LmLgVpF7Jw
TELEGRAM_CHAT_ID=286714512
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/0l42UZmHRHWXBYMJ2QFcdEE-Glj20xqn
```

## ✅ Проверка настройки

После добавления ключей запустите:
```bash
python test_pool_monitoring.py
```

## 🎯 Что будет мониториться после настройки

- **7 Solana пулов**: CURES, SPINE, MYCO пулы
- **12 Ethereum пулов**: VITA, HAIR, GROW, NEURON, CRYO, PSY, QBIO, ATH пулы
- **Алерты**: Транзакции > $10K, продажи DAO/BIO токенов
- **Уведомления**: Telegram бот @daohealthchecker_bot 