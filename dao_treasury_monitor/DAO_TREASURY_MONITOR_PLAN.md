# 🏛️ DAO Treasury Monitor - План развития проекта

## 📋 **Обзор проекта**

**Цель:** Создание системы мониторинга treasury адресов DAO, курируемых BIO Protocol, для отслеживания крупных транзакций и активности в пулах ликвидности.

**Основные функции:**
- Мониторинг исходящих транзакций от treasury адресов (>$10K)
- Отслеживание swaps BIO и DAO токенов
- Мониторинг активности в пулах Raydium и Uniswap
- Real-time уведомления о крупных операциях
- Генерация ежедневных отчетов

---

## 🎯 **Roadmap по приоритетам**

### **📅 Этап 1: MVP - Solana базовый мониторинг** ⏱️ 2-3 дня
**Статус: 🟡 Планируется**

#### ✅ Что используем из существующего кода:
- `HELIUS_API_KEY` и `HELIUS_RPC_URL` 
- `BITQUERY_API_KEY` для исторических данных
- `COINGECKO_API_KEY` для цен токенов
- `TOKEN_SYMBOL_MAP` с BIO и другими токенами
- Функции из `pool_analyzer.py`:
  - `fetch_token_prices_coingecko()`
  - `get_account_info_via_httpx()`
  - `fetch_helius_token_metadata()`

#### 🛠️ Что нужно создать:
- [ ] `dao_config.py` - конфигурация DAO для мониторинга
- [ ] `solana_monitor.py` - мониторинг Solana treasury адресов
- [ ] `database.py` - SQLite база для логирования
- [ ] `main.py` - основной скрипт запуска
- [ ] `requirements.txt` - зависимости проекта

#### 🎯 Результат этапа 1:
- Мониторинг treasury адресов на Solana
- Детекция крупных outgoing транзакций BIO и DAO токенов
- Логирование в SQLite
- Базовые console алерты

---

### **📅 Этап 2: Raydium Pool мониторинг** ⏱️ 1-2 дня  
**Статус: 🟡 Планируется**

#### ✅ Что используем:
- `RAYDIUM_API_V3_BASE_URL`
- Функции из `pool_analyzer.py`:
  - `fetch_raydium_pool_info()`
  - `fetch_bitquery_trade_history()`
  - `fetch_raydium_pool_market_data()`

#### 🛠️ Что нужно создать:
- [ ] `raydium_monitor.py` - мониторинг пулов Raydium
- [ ] `pool_analyzer.py` - анализ add/remove liquidity
- [ ] `volume_tracker.py` - отслеживание объемов торгов

#### 🎯 Результат этапа 2:
- Мониторинг пулов BIO/DAO на Raydium
- Детекция крупных add/remove liquidity
- Tracking объемов продаж DAO токенов

---

### **📅 Этап 3: Ethereum/Uniswap интеграция** ⏱️ 3-4 дня
**Статус: 🔴 Требует новых API**

#### 🛠️ Что нужно добавить:
- [ ] Alchemy API ключ для Ethereum
- [ ] `ethereum_monitor.py` - мониторинг Ethereum treasury
- [ ] `uniswap_monitor.py` - мониторинг Uniswap пулов
- [ ] `web3_utils.py` - утилиты для работы с Ethereum

#### 📋 Новые зависимости:
```bash
web3>=6.0.0
eth-account>=0.9.0
requests>=2.31.0
```

#### 🎯 Результат этапа 3:
- Мониторинг Ethereum treasury адресов
- Мониторинг Uniswap V3 пулов
- Кросс-чейн агрегация данных

---

### **📅 Этап 4: Real-time мониторинг и алерты** ⏱️ 2-3 дня
**Статус: 🔴 Требует дополнительной настройки**

#### 🛠️ Что нужно добавить:
- [ ] WebSocket connections для real-time данных
- [ ] `notification_system.py` - Telegram/Discord алерты
- [ ] `websocket_monitor.py` - real-time transaction monitoring

#### 📋 Новые зависимости:
```bash
websockets>=12.0
python-telegram-bot>=20.0
discord-webhook>=1.0.0
```

#### 🎯 Результат этапа 4:
- Real-time уведомления в Telegram/Discord
- WebSocket мониторинг транзакций
- Instant алерты при крупных операциях

---

### **📅 Этап 5: Railway деплоймент** ⏱️ 1-2 дня
**Статус: 🔴 Требует Railway настройки**

#### 🛠️ Что нужно создать:
- [ ] `railway.toml` - конфигурация деплоймента
- [ ] `Dockerfile` - контейнеризация
- [ ] `health_check.py` - проверка состояния сервиса
- [ ] PostgreSQL миграция с SQLite

#### 🎯 Результат этапа 5:
- Автоматический деплоймент на Railway
- Мониторинг 24/7
- Облачная база данных PostgreSQL

---

## 🏗️ **Техническая архитектура**

### **📁 Структура проекта:**
```
dao_treasury_monitor/
├── DAO_TREASURY_MONITOR_PLAN.md    # Этот файл с планом
├── main.py                         # Основной скрипт запуска
├── requirements.txt                # Python зависимости
├── README.md                       # Документация проекта
├── config/
│   ├── dao_config.py              # Конфигурации DAO
│   └── settings.py                # Общие настройки
├── monitors/
│   ├── solana_monitor.py          # Мониторинг Solana treasury
│   ├── ethereum_monitor.py        # Мониторинг Ethereum treasury
│   ├── raydium_monitor.py         # Мониторинг пулов Raydium
│   └── uniswap_monitor.py         # Мониторинг пулов Uniswap
├── database/
│   ├── database.py                # База данных операции
│   ├── models.py                  # Модели данных
│   └── migrations/                # Миграции БД
├── notifications/
│   ├── notification_system.py     # Система уведомлений
│   ├── telegram_bot.py           # Telegram интеграция
│   └── discord_bot.py            # Discord интеграция
├── utils/
│   ├── web3_utils.py             # Ethereum утилиты
│   ├── price_utils.py            # Утилиты для цен
│   └── format_utils.py           # Форматирование данных
├── tests/
│   └── test_monitors.py          # Unit тесты
└── deploy/
    ├── railway.toml              # Railway конфигурация
    ├── Dockerfile               # Docker контейнер
    └── docker-compose.yml       # Локальная разработка
```

---

## 🔧 **API и зависимости**

### **✅ Имеющиеся API (из pool_analyzer.py):**
```python
# Solana
HELIUS_API_KEY = "d4af7b72-f199-4d77-91a9-11d8512c5e42"
HELIUS_RPC_URL = "https://mainnet.helius-rpc.com/?api-key=..."
BITQUERY_API_KEY = "ory_at_w20OBh_CPS-k6ODVkbnRecl1GAYuOlk363VxvJCvr5A..."
RAYDIUM_API_V3_BASE_URL = "https://api-v3.raydium.io"

# Цены и метаданные
COINGECKO_API_KEY = "CG-9MrJcucBMMx5HKnXeVBD8oSb"
```

### **❌ Требуемые дополнительные API:**
```python
# Ethereum
ALCHEMY_API_KEY = "your_key"  # Для Ethereum RPC
INFURA_PROJECT_ID = "your_id"  # Альтернатива Alchemy

# Уведомления  
TELEGRAM_BOT_TOKEN = "your_token"
DISCORD_WEBHOOK_URL = "your_webhook"

# The Graph Protocol
UNISWAP_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
```

### **📦 Python зависимости:**
```txt
# Базовые (уже есть в pool_analyzer.py)
httpx>=0.25.0
asyncio>=3.4.3
python-dotenv>=1.0.0

# Blockchain
web3>=6.0.0
solders>=0.18.0
construct>=2.10.0

# База данных
sqlite3  # Встроен в Python
psycopg2-binary>=2.9.0  # Для PostgreSQL на Railway

# Уведомления
python-telegram-bot>=20.0
discord-webhook>=1.0.0
websockets>=12.0

# Утилиты
schedule>=1.2.0
python-dateutil>=2.8.0
```

---

## 🎯 **DAO конфигурации для мониторинга**

### **🧬 VitaDAO:**
```python
VitaDAO = DAOConfig(
    name="VitaDAO",
    treasury_addresses_solana=[
        # Нужно найти адреса VitaDAO treasury на Solana
    ],
    treasury_addresses_ethereum=[
        "0x...",  # VitaDAO treasury на Ethereum
    ],
    token_mint_solana="VITA...",
    token_contract_ethereum="0x...",
    bio_pools_raydium=[
        # Пулы BIO/VITA на Raydium
    ],
    bio_pools_uniswap=[
        # Пулы BIO/VITA на Uniswap
    ]
)
```

### **🔬 Дополнительные DAO:**
- [ ] **ValleyDAO** - синтетическая биология
- [ ] **CryoDAO** - крионические исследования
- [ ] **HairDAO** - исследования волос
- [ ] **PsyDAO** - психоделические исследования
- [ ] **AthenaDAO** - женское здоровье

---

## 📊 **Мониторинг метрики**

### **🚨 Алерты (>$10K USD):**
- ✅ Исходящие transfers BIO/DAO токенов от treasury
- ✅ Swaps BIO/DAO токенов в другие валюты
- ✅ Крупные add/remove liquidity в пулах
- ✅ Аномальные объемы торгов

### **📈 Ежедневные отчеты:**
- ✅ Суммарные объемы по каждому DAO
- ✅ Изменения в treasury балансах
- ✅ Активность в пулах ликвидности
- ✅ ТОП транзакции за день

### **📊 Dashboard метрики:**
- ✅ Real-time treasury балансы
- ✅ 24h торговые объемы
- ✅ Liquidity pool TVL изменения
- ✅ Price impact от крупных сделок

---

## ✅ **Чек-лист прогресса**

### **Этап 1: MVP - Solana мониторинг**
- [ ] Создать базовую структуру проекта
- [ ] Настроить DAO конфигурации
- [ ] Реализовать Solana treasury мониторинг
- [ ] Добавить SQLite логирование
- [ ] Протестировать на реальных данных

### **Этап 2: Raydium Pool мониторинг**
- [ ] Интеграция с Raydium API
- [ ] Мониторинг add/remove liquidity
- [ ] Tracking объемов торгов
- [ ] Алерты по pool активности

### **Этап 3: Ethereum/Uniswap**
- [ ] Получить Alchemy API ключ
- [ ] Реализовать Ethereum мониторинг
- [ ] Интеграция с Uniswap V3
- [ ] Кросс-чейн агрегация

### **Этап 4: Real-time и алерты**
- [ ] WebSocket connections
- [ ] Telegram/Discord боты
- [ ] Real-time уведомления
- [ ] Advanced алерт логика

### **Этап 5: Railway деплоймент**
- [ ] Создать Railway проект
- [ ] Настроить PostgreSQL
- [ ] Автоматический деплоймент
- [ ] Мониторинг и логи

---

## 🚀 **Следующие шаги**

1. **Немедленно:** Начать с Этапа 1 - создание базовой структуры
2. **Сегодня:** Настроить DAO конфигурации и Solana мониторинг
3. **Завтра:** Добавить Raydium pool мониторинг
4. **На неделе:** Получить Ethereum API и добавить кросс-чейн функциональность
5. **Через неделю:** Деплой на Railway с full functionality

---

**💡 Примечание:** Этот план будет обновляться по мере прогресса. Каждый завершенный этап будет отмечаться как ✅, а текущий прогресс - как 🟡.

**📝 Последнее обновление:** 9 декабря 2024 