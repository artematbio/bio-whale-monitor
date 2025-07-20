# 🐋 BIO Whale Monitor

Мониторинг крупных исходящих транзакций BIO и vBIO токенов на Ethereum блокчейне.

## 🎯 Описание

BIO Whale Monitor - это система мониторинга, которая отслеживает крупные исходящие транзакции BIO и vBIO токенов от указанного списка кошельков. Система отправляет уведомления в Telegram при обнаружении транзакций, превышающих настроенные пороговые значения.

## 📊 Функциональность

### Основные возможности
- 🐋 **Мониторинг whale транзакций** - отслеживание крупных переводов BIO/vBIO
- 💰 **Двойная фильтрация** - по количеству токенов ИЛИ по USD стоимости
- 📱 **Telegram уведомления** - мгновенные алерты с деталями транзакции
- 🗄️ **База данных** - сохранение истории whale транзакций
- 🔄 **Real-time мониторинг** - проверка каждые 30 секунд
- 🌐 **Railway деплой** - готов к производственному развертыванию

### Пороговые значения
- **Количество токенов**: ≥1,000,000 BIO/vBIO
- **USD стоимость**: ≥$100,000
- **Источник**: только от отслеживаемых кошельков
- **Направление**: только исходящие транзакции

## 🚀 Быстрый старт

### 1. Настройка переменных окружения

Создайте файл `.env`:

```bash
# Ethereum RPC (обязательно)
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Telegram (обязательно для уведомлений)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# База данных (опционально, для Railway)
DATABASE_URL=postgresql://user:password@host:port/dbname

# CoinGecko API (опционально, для цен)
COINGECKO_API_KEY=your_coingecko_api_key

# Railway (автоматически)
RAILWAY_ENVIRONMENT=production
PORT=8080
```

### 2. Добавление кошельков для мониторинга

Отредактируйте `config/whale_config.py`:

```python
MONITORED_WALLETS = [
    "0x1234567890123456789012345678901234567890",  # Кошелек 1
    "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",  # Кошелек 2
    # Добавьте свои адреса
]
```

### 3. Проверка адресов BIO токенов

В `config/whale_config.py` убедитесь что адреса токенов корректны:

```python
BIO_TOKENS = {
    "BIO": {
        "contract_address": "0xcbb7C0000aB88B473b1f5aFd9ef808440eed33Bf",  # Проверьте адрес
        "symbol": "BIO",
        "decimals": 18,
        "name": "BIO Protocol"
    },
    "vBIO": {
        "contract_address": "0x1234567890123456789012345678901234567890",  # НУЖНО УТОЧНИТЬ!
        "symbol": "vBIO", 
        "decimals": 18,
        "name": "Voting BIO"
    }
}
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Запуск

```bash
# Тестовый режим
python main.py --mode test

# Показать конфигурацию
python main.py --mode status

# Запуск мониторинга
python main.py --mode monitor
```

## 📋 Конфигурация

### Файлы конфигурации

- `config/whale_config.py` - основная конфигурация whale мониторинга
- `.env` - переменные окружения

### Настройки мониторинга

```python
# В config/whale_config.py
WHALE_THRESHOLDS = {
    "token_amount": 1_000_000,  # 1 миллион токенов
    "usd_amount": 100_000,      # $100,000 USD
}

MONITORING_CONFIG = {
    "check_interval": 30,       # Интервал проверки в секундах
    "blocks_lookback": 5,       # Количество блоков для проверки назад
    "retry_attempts": 3,
    "retry_delay": 5,
}
```

## 📨 Формат уведомлений

При обнаружении whale транзакции вы получите уведомление:

```
🐋 WHALE ALERT: Large BIO Transfer

💰 Amount: 2,500,000.00 BIO
💵 USD Value: $375,000.00

📤 From: 0x1234...7890
📥 To: 0xabcd...efgh

🔗 Transaction: 0xdef456...
🌐 Etherscan: https://etherscan.io/tx/0xdef456...

⏰ Time: 2025-06-18 12:34:56 UTC
🚨 Alert Triggered: Token amount threshold exceeded
```

## 🔧 Управление

### Команды

```bash
# Мониторинг (основной режим)
python main.py --mode monitor

# Тестирование подключений
python main.py --mode test

# Показать статус и конфигурацию
python main.py --mode status

# Тест уведомлений
python main.py --mode test-alerts

# С логированием в файл
python main.py --mode monitor --log-file whale_monitor.log

# Уровень логирования
python main.py --mode monitor --log-level DEBUG
```

### Добавление кошельков

Для добавления новых кошельков для мониторинга:

```python
# В config/whale_config.py
from config.whale_config import add_monitored_wallet

# Добавление через функцию (с валидацией)
add_monitored_wallet("0x1234567890123456789012345678901234567890")

# Или прямо в список
MONITORED_WALLETS.append("0x1234567890123456789012345678901234567890")
```

## 🚀 Деплой на Railway

### 1. Подключение к Railway

```bash
# Инициализация
railway login
railway init

# Связывание с проектом
railway link [project-id]
```

### 2. Переменные окружения Railway

В Railway панели настройте:

- `ETHEREUM_RPC_URL` - ваш Alchemy/Infura endpoint
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `TELEGRAM_CHAT_ID` - ID чата для уведомлений
- `DATABASE_URL` - автоматически (PostgreSQL addon)

### 3. Деплой

```bash
# Автоматический деплой при push в main
git push origin main

# Или через Railway CLI
railway up
```

## 📊 База данных

### SQLite (локальная разработка)
- Файл: `dao_treasury.db`
- Создается автоматически

### PostgreSQL (Railway)
- Используется автоматически при наличии `DATABASE_URL`
- Миграции выполняются при запуске

### Схема данных

```sql
-- Таблица транзакций
CREATE TABLE treasury_transactions (
    id INTEGER PRIMARY KEY,
    transaction_hash TEXT UNIQUE,
    from_address TEXT,
    to_address TEXT,
    token_symbol TEXT,
    token_amount REAL,
    usd_value REAL,
    transaction_type TEXT,
    timestamp DATETIME,
    block_number INTEGER
);

-- Таблица алертов
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    transaction_hash TEXT,
    alert_type TEXT,
    message TEXT,
    sent_at DATETIME,
    success BOOLEAN
);
```

## 🛠️ Разработка

### Структура проекта

```
bio-whale-monitor/
├── main.py                     # Точка входа
├── config/
│   └── whale_config.py         # Конфигурация whale мониторинга
├── monitors/
│   └── bio_whale_monitor.py    # Основной whale мониторинг
├── database/
│   ├── database.py             # SQLite адаптер
│   └── postgresql_database.py  # PostgreSQL адаптер
├── notifications/
│   ├── telegram_bot.py         # Telegram бот
│   └── notification_system.py  # Система уведомлений
├── utils/
│   └── price_utils.py          # Утилиты для работы с ценами
├── health_check.py             # Health check для Railway
├── requirements.txt            # Python зависимости
├── Dockerfile                  # Docker конфигурация
├── railway.toml               # Railway конфигурация
└── README.md                  # Документация
```

### Добавление новых токенов

```python
# В config/whale_config.py
BIO_TOKENS["NEW_TOKEN"] = {
    "contract_address": "0x...",
    "symbol": "NEW",
    "decimals": 18,
    "name": "New Token"
}
```

### Кастомизация пороговых значений

```python
# В config/whale_config.py
WHALE_THRESHOLDS = {
    "token_amount": 500_000,    # Снизить до 500k токенов
    "usd_amount": 50_000,       # Снизить до $50k
}
```

## 🔍 Мониторинг и отладка

### Логи

```bash
# Просмотр логов Railway
railway logs

# Локальные логи
tail -f whale_monitor.log
```

### Health Check

- **URL**: `https://your-app.railway.app/health`
- **Статус**: показывает время последней активности

### Диагностика

```bash
# Проверка подключения к Ethereum
python -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))
print(f'Connected: {w3.is_connected()}')
print(f'Latest block: {w3.eth.block_number}')
"

# Проверка контрактов токенов
python main.py --mode test
```

## ⚠️ Важные заметки

### Безопасность
- 🔐 Никогда не коммитьте `.env` файл
- 🔑 Используйте надежные API ключи
- 🛡️ Ограничьте доступ к Telegram боту

### Производительность
- ⚡ Мониторинг работает каждые 30 секунд
- 📦 Сканирует последние 5 блоков
- 💾 Автоматически предотвращает дубликаты

### Ограничения
- 🔄 Зависит от стабильности RPC провайдера
- 📊 Цены обновляются каждые 5 минут
- 🐋 Работает только с ERC-20 токенами

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи: `railway logs` или локальный лог файл
2. Убедитесь что все переменные окружения настроены
3. Проверьте валидность адресов кошельков и токенов
4. Протестируйте подключения: `python main.py --mode test`

## 📄 Лицензия

Этот проект является форком DAO Treasury Monitor и наследует его лицензию. 