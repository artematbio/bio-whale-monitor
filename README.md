# 🏛️ DAO Treasury Monitor

Real-time monitoring system for BIO Protocol DAO treasury transactions and token activities.

## 🚀 **Features**

- **24/7 Treasury Monitoring**: Tracks treasury transactions >$10K across multiple DAOs
- **Real-time Telegram Alerts**: Instant notifications for large transactions and price movements
- **Price Tracking**: Monitors BIO and DAO token price changes with alerts for >5% drops
- **Multi-blockchain Support**: Solana (active) + Ethereum (planned)
- **Production Ready**: Railway deployment with PostgreSQL, health checks, and auto-scaling

## 📊 **Currently Monitoring**

- **11 DAOs**: VitaDAO, ValleyDAO, CryoDAO, HairDAO, PsyDAO, AthenaDAO, and more
- **4 Active Treasury Addresses** on Solana
- **13 Tokens**: BIO, VITA, and other DAO tokens
- **Alert Threshold**: $10,000 USD

## 🔧 **Technology Stack**

- **Backend**: Python 3.11, FastAPI, aiohttp
- **Database**: PostgreSQL (production) / SQLite (development)
- **Blockchain APIs**: Helius (Solana), CoinGecko (prices)
- **Notifications**: Telegram Bot API
- **Deployment**: Railway with Docker, health checks, auto-restart

## 🚀 **Railway Deployment**

### Quick Setup:
1. Fork this repository
2. Create Railway project and connect GitHub
3. Add PostgreSQL service
4. Set environment variables:
   ```bash
   HELIUS_API_KEY=your_helius_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   COINGECKO_API_KEY=your_coingecko_key
   ```
5. Deploy automatically

### Health Check Endpoints:
- `/health` - System health status
- `/status` - Detailed system information  
- `/metrics` - Performance metrics

## 📱 **Telegram Bot Setup**

1. Create bot with [@BotFather](https://t.me/botfather)
2. Get bot token and your chat ID
3. Add to Railway environment variables
4. Bot will send alerts for:
   - Treasury transactions >$10K
   - Token price drops >5%
   - Daily summaries

## 🔍 **Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Run different modes
python main.py --mode monitor     # Start monitoring
python main.py --mode test        # Test connections
python main.py --mode status      # Show system status
python main.py --mode test-alerts # Test Telegram alerts
```

## 📈 **Monitoring Coverage**

### Solana Treasury Addresses:
- VitaDAO: `7QuWPKmgtVJ5cydTXYPk9EEtQDC3Loo8EPiB2kZRBhP4`
- Other DAOs: Additional addresses configured

### Supported Tokens:
- BIO Protocol tokens (Ethereum & Solana)
- DAO-specific tokens (VITA, etc.)
- Real-time price tracking via CoinGecko

## 🛡️ **Security & Performance**

- **Environment Variables**: All API keys secured
- **Connection Pooling**: Optimized database connections
- **Rate Limiting**: Respectful API usage
- **Error Handling**: Robust retry logic and fallbacks
- **Health Monitoring**: Auto-restart on failures

## 📊 **Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Blockchain    │    │   DAO Treasury   │    │    Telegram     │
│   APIs (Helius,│───▶│    Monitor       │───▶│   Notifications │
│   CoinGecko)    │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   PostgreSQL     │
                       │   Database       │
                       └──────────────────┘
```

## 🚀 **Ready for Production**

This system is production-ready with:
- ✅ Automatic Railway deployment
- ✅ Health checks and monitoring
- ✅ PostgreSQL database with backups
- ✅ Real-time Telegram notifications
- ✅ 24/7 treasury monitoring
- ✅ Scalable architecture

---

**Live monitoring of DAO treasuries with instant alerts for significant activities.**

## 🎯 Основные функции

- 📊 **Мониторинг Treasury:** Отслеживание исходящих транзакций от treasury адресов (>$10K)
- 🔄 **Swap мониторинг:** Детекция swaps BIO и DAO токенов в другие валюты  
- 🏊 **Pool активность:** Мониторинг add/remove liquidity в пулах Raydium и Uniswap
- 🚨 **Real-time алерты:** Уведомления о крупных операциях в Telegram/Discord
- 📈 **Ежедневные отчеты:** Агрегация данных и analytics

## 🏗️ Архитектура

```
dao_treasury_monitor/
├── main.py                    # Точка входа
├── config/                    # Конфигурации DAO
├── monitors/                  # Мониторинг модули  
├── database/                  # База данных
├── notifications/             # Система уведомлений
├── utils/                     # Утилиты
└── deploy/                    # Деплоймент конфиги
```

## ⚡ Быстрый старт

### Установка зависимостей:
```bash
cd dao_treasury_monitor
pip install -r requirements.txt
```

### Настройка переменных окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими API ключами
```

### Запуск мониторинга:
```bash
python main.py
```

## 🔧 Конфигурация

Основные настройки в `config/settings.py`:
- API ключи для Helius, CoinGecko, Alchemy
- Пороги для алертов ($10K по умолчанию)
- Интервалы мониторинга
- Telegram/Discord настройки

DAO конфигурации в `config/dao_config.py`:
- Treasury адреса на Solana и Ethereum
- Токены для мониторинга
- Пулы ликвидности

## 📊 Мониторимые DAO

- 🧬 **VitaDAO** - Longevity research
- 🧪 **ValleyDAO** - Синтетическая биология
- ❄️ **CryoDAO** - Крионические исследования
- 💇 **HairDAO** - Исследования волос
- 🍄 **PsyDAO** - Психоделические исследования
- 👩 **AthenaDAO** - Женское здоровье

## 🚀 Roadmap

Подробный план развития см. в [DAO_TREASURY_MONITOR_PLAN.md](DAO_TREASURY_MONITOR_PLAN.md)

### Этап 1: ✅ MVP - Solana мониторинг
### Этап 2: 🟡 Raydium Pool мониторинг  
### Этап 3: 🔴 Ethereum/Uniswap интеграция
### Этап 4: 🔴 Real-time алерты
### Этап 5: 🔴 Railway деплоймент

## 📝 API Requirements

### ✅ Уже настроенные:
- Helius API (Solana RPC)
- CoinGecko API (цены токенов)
- Bitquery API (исторические данные)
- Raydium API v3

### ❌ Требуются дополнительно:
- Alchemy API (Ethereum RPC)
- Telegram Bot Token
- Discord Webhook URL

## 🤝 Contributing

1. Fork репозиторий
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request

## 📄 License

MIT License - см. [LICENSE](LICENSE) файл

## 🔗 Links

- [BIO Protocol](https://www.bioprotocol.com/)
- [Raydium](https://raydium.io/)
- [Uniswap](https://uniswap.org/)
- [Railway](https://railway.app/)

---

**Последнее обновление:** 9 декабря 2024 