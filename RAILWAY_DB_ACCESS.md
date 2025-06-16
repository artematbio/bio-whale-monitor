# 📊 Доступ к базе данных Railway

## 🚀 Как посмотреть базу данных на Railway

Для просмотра базы данных на Railway есть несколько способов:

### 🔧 Способ 1: Через локальную настройку

1. **Получите DATABASE_URL из Railway:**
   - Зайдите в Railway dashboard
   - Откройте ваш проект DAO Treasury Monitor
   - Перейдите в раздел Variables
   - Скопируйте значение `DATABASE_URL`

2. **Добавьте DATABASE_URL в .env файл:**
   ```bash
   echo "DATABASE_URL=postgresql://username:password@host:port/dbname" >> .env
   ```
   (замените на ваш настоящий DATABASE_URL из Railway)

3. **Используйте команды для Railway:**
   ```bash
   # Загрузить алиасы
   source db_shortcuts.sh
   
   # Посмотреть Railway базу данных
   dbrailwaystats           # Статистика Railway БД
   dbrailwaytx5             # Последние 5 транзакций
   dbrailwayalerts5         # Последние 5 алертов
   dbrailway                # Полный обзор Railway БД
   ```

### 🌐 Способ 2: Через Railway CLI

1. **Установите Railway CLI:**
   ```bash
   brew install railway
   # или
   npm install -g @railway/cli
   ```

2. **Войдите в Railway:**
   ```bash
   railway login
   ```

3. **Подключитесь к базе данных:**
   ```bash
   railway connect postgresql
   ```

### 💻 Способ 3: Через Railway Web Console

1. Откройте Railway dashboard
2. Выберите ваш проект
3. Откройте PostgreSQL service
4. Перейдите в раздел "Data" или "Query"
5. Используйте встроенный SQL редактор

### 📋 Доступные команды для просмотра БД

После настройки DATABASE_URL:

```bash
# Автоопределение (Railway если доступен)
dbstats              # Статистика
dbtx                 # Транзакции
dbalerts             # Алерты
dbconnection         # Информация о подключении

# Принудительно Railway
dbrailwaystats       # Статистика Railway
dbrailwaytx          # Транзакции Railway
dbrailwayalerts      # Алерты Railway
dbrailwayprices      # Цены токенов Railway
dbrailwaydao         # Сводка по DAO

# Принудительно локальная
dblocalstats         # Статистика локальной БД
dblocaltx            # Транзакции локальные
dblocalalerts        # Алерты локальные
```

### 🔍 Примеры SQL запросов

Если у вас есть прямой доступ к PostgreSQL:

```sql
-- Статистика базы данных
SELECT 
    'treasury_transactions' as table_name, COUNT(*) as records 
FROM treasury_transactions
UNION ALL
SELECT 'alerts', COUNT(*) FROM alerts
UNION ALL
SELECT 'token_prices', COUNT(*) FROM token_prices;

-- Последние транзакции
SELECT dao_name, blockchain, token_symbol, amount_usd, timestamp
FROM treasury_transactions 
ORDER BY timestamp DESC 
LIMIT 10;

-- Последние алерты
SELECT dao_name, alert_type, severity, title, timestamp
FROM alerts 
ORDER BY timestamp DESC 
LIMIT 10;

-- Активность по DAO
SELECT dao_name, blockchain, COUNT(*) as tx_count, SUM(amount_usd) as total_usd
FROM treasury_transactions 
GROUP BY dao_name, blockchain
ORDER BY total_usd DESC;
```

### 🚨 Важные замечания

1. **Безопасность**: Никогда не коммитьте DATABASE_URL в git
2. **Разные базы**: Railway (PostgreSQL) и локальная (SQLite) могут содержать разные данные
3. **Синхронизация**: Данные записываются только когда система мониторинга работает
4. **Права доступа**: Убедитесь что у вас есть права для подключения к Railway БД

### 🛠️ Диагностика проблем

```bash
# Проверить доступность модулей
python3 -c "import psycopg2; print('PostgreSQL модуль доступен')"

# Проверить переменные окружения
echo "DATABASE_URL установлен: $DATABASE_URL"

# Проверить подключение
dbconnection

# Принудительно попробовать Railway
python3 database_viewer.py --railway --mode connection
``` 