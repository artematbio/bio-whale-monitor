#!/bin/bash
# DAO Treasury Monitor - Database Shortcuts
# Удобные команды для просмотра базы данных

echo "🚀 DAO Treasury Monitor - Database Shortcuts"
echo "=============================================="

# Основные команды (автоопределение)
alias dbview='python3 database_viewer.py'
alias dbstats='python3 database_viewer.py --mode stats'
alias dbtx='python3 database_viewer.py --mode transactions'
alias dbalerts='python3 database_viewer.py --mode alerts'
alias dbprices='python3 database_viewer.py --mode prices'
alias dbtables='python3 database_viewer.py --mode tables'
alias dbdao='python3 database_viewer.py --mode dao'
alias dbconnection='python3 database_viewer.py --mode connection'

# Команды для локальной базы данных (SQLite)
alias dblocal='python3 database_viewer.py --local'
alias dblocalstats='python3 database_viewer.py --local --mode stats'
alias dblocaltx='python3 database_viewer.py --local --mode transactions'
alias dblocalalerts='python3 database_viewer.py --local --mode alerts'

# Команды для Railway базы данных (PostgreSQL)
alias dbrailway='python3 database_viewer.py --railway'
alias dbrailwaystats='python3 database_viewer.py --railway --mode stats'
alias dbrailwaytx='python3 database_viewer.py --railway --mode transactions'
alias dbrailwayalerts='python3 database_viewer.py --railway --mode alerts'
alias dbrailwayprices='python3 database_viewer.py --railway --mode prices'
alias dbrailwaytables='python3 database_viewer.py --railway --mode tables'
alias dbrailwaydao='python3 database_viewer.py --railway --mode dao'

# Интерактивный Railway просмотрщик
alias railwaydb='python3 railway_db_viewer.py'

# Команды с лимитами (автоопределение)
alias dbtx5='python3 database_viewer.py --mode transactions --limit 5'
alias dbtx20='python3 database_viewer.py --mode transactions --limit 20'
alias dbalerts5='python3 database_viewer.py --mode alerts --limit 5'
alias dbalerts20='python3 database_viewer.py --mode alerts --limit 20'

# Railway команды с лимитами
alias dbrailwaytx5='python3 database_viewer.py --railway --mode transactions --limit 5'
alias dbrailwaytx20='python3 database_viewer.py --railway --mode transactions --limit 20'
alias dbrailwayalerts5='python3 database_viewer.py --railway --mode alerts --limit 5'
alias dbrailwayalerts20='python3 database_viewer.py --railway --mode alerts --limit 20'

echo "Available commands:"
echo ""
echo "📊 AUTO-DETECT (local if no DATABASE_URL, Railway if available):"
echo "  dbview         - Show all database content"
echo "  dbstats        - Show database statistics"
echo "  dbconnection   - Show connection info"
echo "  dbtx / dbtx5   - Show transactions (default 10 / last 5)"
echo "  dbalerts       - Show recent alerts"
echo ""
echo "🏠 LOCAL DATABASE (SQLite):"
echo "  dblocal        - Show all local database content"
echo "  dblocalstats   - Show local database statistics" 
echo "  dblocaltx      - Show local transactions"
echo "  dblocalalerts  - Show local alerts"
echo ""
echo "🚂 RAILWAY DATABASE (PostgreSQL):"
echo "  dbrailway      - Show all Railway database content"
echo "  dbrailwaystats - Show Railway database statistics"
echo "  dbrailwaytx    - Show Railway transactions"
echo "  dbrailwaytx5   - Show last 5 Railway transactions"
echo "  dbrailwayalerts- Show Railway alerts"
echo "  dbrailwayprices- Show Railway price data"
echo "  railwaydb      - Interactive Railway database viewer"
echo ""
echo "Usage examples:"
echo "  source db_shortcuts.sh  # Load shortcuts"
echo "  dbconnection            # Check which database is used"
echo "  railwaydb               # Interactive Railway database viewer"
echo "  dbrailwaystats          # Railway database stats"
echo "  dblocalstats            # Local database stats"
echo "  dbrailwaytx5            # Last 5 Railway transactions"
echo "=============================================="
alias testprices='python3 -c "from monitors.price_tracker import PriceTracker; from database.database import DAOTreasuryDatabase; import asyncio; db = DAOTreasuryDatabase(); tracker = PriceTracker(db); asyncio.run(tracker.run_price_tracking_cycle())"'
