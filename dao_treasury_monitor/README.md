# 🏛️ DAO Treasury Monitor

Система мониторинга treasury адресов DAO, курируемых BIO Protocol, для отслеживания крупных транзакций и активности в пулах ликвидности на Solana (Raydium) и Ethereum (Uniswap).

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