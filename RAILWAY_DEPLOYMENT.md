# 🚀 Railway Deployment Guide для DAO Treasury Monitor

## 📋 **Готовность к деплойменту**

### ✅ **Что готово:**
- [x] Основной мониторинг Solana транзакций
- [x] Telegram уведомления
- [x] Price tracking с алертами
- [x] SQLite база данных (для локальной разработки)
- [x] PostgreSQL адаптер (для Railway)
- [x] Health check endpoint (`/health`, `/status`, `/metrics`)
- [x] Dockerfile с оптимизированным образом
- [x] Railway configuration (`railway.toml`)
- [x] Автоматический restart при сбоях
- [x] Graceful shutdown при остановке

### ⚠️ **Что нужно настроить на Railway:**

#### **1. Переменные окружения (Environment Variables):**

**Обязательные для работы:**
```bash
# Solana API
HELIUS_API_KEY=d4af7b72-f199-4d77-91a9-11d8512c5e42
HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=d4af7b72-f199-4d77-91a9-11d8512c5e42

# Telegram уведомления
TELEGRAM_BOT_TOKEN=7132907460:AAGCduLmhc5njQ43C_PMyGfG1LmLgVpF7Jw
TELEGRAM_CHAT_ID=286714512

# CoinGecko API
COINGECKO_API_KEY=CG-9MrJcucBMMx5HKnXeVBD8oSb

# Мониторинг настройки
ALERT_THRESHOLD_USD=10000
MONITORING_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

**Автоматически добавляются Railway:**
```bash
# Database (PostgreSQL автоматически)
DATABASE_URL=postgresql://...

# Port для health check
PORT=8080

# Railway environment
RAILWAY_ENVIRONMENT=production
```

#### **2. Услуги Railway:**
- **PostgreSQL Database** - добавить как дополнительный сервис
- **Railway App** - основное приложение

---

## 🚀 **Инструкции по деплойменту**

### **Шаг 1: Подготовка репозитория**

1. **Убедитесь что все файлы на месте:**
```bash
dao_treasury_monitor/
├── railway.toml              ✅ Готов
├── Dockerfile               ✅ Готов  
├── requirements.txt         ✅ Обновлен с PostgreSQL
├── main.py                  ✅ Обновлен с health check
├── health_check.py          ✅ Создан
├── database/
│   ├── database.py          ✅ SQLite (локально)
│   └── postgresql_database.py ✅ PostgreSQL (Railway)
└── [остальные файлы]
```

2. **Пуш в Git репозиторий:**
```bash
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

### **Шаг 2: Создание Railway проекта**

1. **Зайти на [railway.app](https://railway.app/)**
2. **Подключить GitHub репозиторий**
3. **Выбрать директорию:** `/dao_treasury_monitor`
4. **Deploy project**

### **Шаг 3: Добавление PostgreSQL**

1. **В проекте нажать "Add Service"**
2. **Выбрать "PostgreSQL"**
3. **Railway автоматически создаст `DATABASE_URL`**

### **Шаг 4: Настройка Environment Variables**

В Railway dashboard добавить переменные:

```bash
HELIUS_API_KEY=d4af7b72-f199-4d77-91a9-11d8512c5e42
TELEGRAM_BOT_TOKEN=7132907460:AAGCduLmhc5njQ43C_PMyGfG1LmLgVpF7Jw
TELEGRAM_CHAT_ID=286714512
COINGECKO_API_KEY=CG-9MrJcucBMMx5HKnXeVBD8oSb
ALERT_THRESHOLD_USD=10000
MONITORING_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### **Шаг 5: Проверка деплоймента**

1. **Health Check:**
   - URL: `https://your-app.railway.app/health`
   - Должен вернуть: `{"status": "healthy", "timestamp": "...", "checks": {...}}`

2. **Status endpoint:**
   - URL: `https://your-app.railway.app/status`
   - Показывает детальную информацию о системе

3. **Metrics:**
   - URL: `https://your-app.railway.app/metrics`
   - Метрики для мониторинга

4. **Проверка логов в Railway Dashboard**

---

## 🔍 **Мониторинг и обслуживание**

### **Health Checks:**
- **Railway автоматически проверяет:** `/health` каждые 30 секунд
- **Restart при сбое:** автоматический перезапуск если health check fails
- **Timeout:** 5 минут на запуск

### **Логирование:**
- **Все логи доступны в Railway Dashboard**
- **Уровень:** `INFO` (можно изменить через `LOG_LEVEL`)
- **Structured logs** с timestamp и context

### **Database Backups:**
- **PostgreSQL on Railway:** автоматические бэкапы
- **Migration:** автоматическая миграция с SQLite данных

### **Scaling:**
- **CPU/Memory:** автоматический scaling
- **Connection pooling:** оптимизировано для PostgreSQL
- **Concurrent connections:** до 20 одновременных

---

## 🛡️ **Безопасность**

### **Environment Variables:**
- **Все API ключи в environment variables**
- **Не хранятся в коде**
- **Безопасная передача через Railway**

### **Database:**
- **PostgreSQL с SSL**
- **Connection pooling с автоматическим cleanup**
- **Prepared statements для защиты от SQL injection**

### **Network:**
- **Health check endpoints открыты**
- **Все остальные endpoints закрыты**
- **HTTPS only через Railway**

---

## ⚡ **Performance Optimization**

### **Database:**
- **Connection pooling:** 1-20 connections
- **Indexing:** оптимизированные индексы для всех таблиц
- **Efficient queries:** prepared statements

### **Monitoring:**
- **Асинхронный мониторинг:** параллельные задачи
- **Rate limiting:** умные интервалы запросов
- **Caching:** price data caching

### **Memory:**
- **Efficient data structures**
- **Cleanup старых данных автоматически**
- **Minimal Docker image:** Python 3.11-slim

---

## 🔧 **Troubleshooting**

### **Если health check fails:**
1. Проверить логи в Railway Dashboard
2. Проверить DATABASE_URL переменную
3. Проверить TELEGRAM_BOT_TOKEN

### **Если нет уведомлений в Telegram:**
1. Проверить `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`
2. Убедиться что бот добавлен в чат
3. Проверить endpoint: `/status` для диагностики

### **Если нет мониторинга транзакций:**
1. Проверить `HELIUS_API_KEY`
2. Проверить логи Solana monitor
3. Проверить database connectivity

---

## 📊 **Мониторинг метрик через endpoints**

### **GET /health**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-09T10:30:00Z",
  "checks": {
    "database": {"status": "ok", "message": "Database accessible"},
    "activity": {"status": "ok", "message": "Recent activity: 3 alerts in last 2h"},
    "environment": {"status": "ok", "message": "All required environment variables set"}
  }
}
```

### **GET /status**
```json
{
  "system": {
    "uptime": 3600,
    "timestamp": "2024-12-09T10:30:00Z",
    "environment": "production"
  },
  "database": {
    "treasury_transactions": 150,
    "alerts": 45,
    "database_size_mb": 15.2
  },
  "monitoring": {
    "alerts_last_24h": 8,
    "last_activity": "2024-12-09T10:29:00Z"
  }
}
```

### **GET /metrics**
```json
{
  "treasury_transactions_total": 150,
  "pool_activities_total": 200,
  "alerts_total": 45,
  "database_size_mb": 15.2,
  "uptime_seconds": 3600
}
```

---

## ✅ **Готовность к production**

**Система полностью готова к деплойменту на Railway с следующими возможностями:**

1. **✅ 24/7 мониторинг:** Постоянное отслеживание DAO treasury транзакций
2. **✅ Real-time алерты:** Telegram уведомления при крупных операциях
3. **✅ Health monitoring:** Автоматический restart при сбоях
4. **✅ Scalable database:** PostgreSQL с connection pooling
5. **✅ Production logging:** Structured logs с метриками
6. **✅ Security:** Все ключи в environment variables
7. **✅ Performance:** Оптимизированные запросы и асинхронная обработка

**Время деплоймента: ~10-15 минут**
**Время готовности после деплоймента: ~2-3 минуты**

**После успешного деплоймента система будет автоматически:**
- Мониторить VitaDAO и другие DAO treasury адреса
- Отправлять Telegram алерты при транзакциях >$10K
- Отслеживать изменения цен BIO и DAO токенов
- Логировать всю активность в PostgreSQL
- Предоставлять health check endpoints для мониторинга 