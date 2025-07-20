#!/usr/bin/env python3
"""
Health Check Server для DAO Treasury Monitor
Обеспечивает health check endpoint для Railway deployment
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import uvicorn

from database.database import DAOTreasuryDatabase

logger = logging.getLogger(__name__)

class HealthCheckServer:
    """Health Check сервер для мониторинга состояния приложения"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = FastAPI(title="DAO Treasury Monitor Health Check")
        self.database = None
        self.last_activity_time = datetime.now()
        
        # Настройка endpoints
        self.setup_routes()
    
    def setup_routes(self):
        """Настройка маршрутов FastAPI"""
        
        @self.app.get("/health")
        async def health_check():
            """Основной health check endpoint"""
            try:
                health_status = await self._check_system_health()
                
                if health_status['status'] == 'healthy':
                    return JSONResponse(
                        status_code=200,
                        content=health_status
                    )
                else:
                    return JSONResponse(
                        status_code=503,
                        content=health_status
                    )
                    
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        'status': 'unhealthy',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                )
        
        @self.app.get("/status")
        async def detailed_status():
            """Детальная информация о состоянии системы"""
            try:
                return await self._get_detailed_status()
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={'error': str(e)}
                )
        
        @self.app.get("/metrics")
        async def metrics():
            """Метрики для мониторинга"""
            try:
                return await self._get_metrics()
            except Exception as e:
                logger.error(f"Metrics check failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={'error': str(e)}
                )
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Проверка здоровья системы"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Проверка базы данных
        db_healthy = await self._check_database_health()
        health_status['checks']['database'] = db_healthy
        
        # Проверка последней активности
        activity_healthy = await self._check_activity_health()
        health_status['checks']['activity'] = activity_healthy
        
        # Проверка переменных окружения
        env_healthy = await self._check_environment_health()
        health_status['checks']['environment'] = env_healthy
        
        # Общий статус
        all_checks_healthy = all([
            db_healthy['status'] == 'ok',
            activity_healthy['status'] == 'ok',
            env_healthy['status'] == 'ok'
        ])
        
        if not all_checks_healthy:
            health_status['status'] = 'unhealthy'
        
        return health_status
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Проверка состояния базы данных"""
        try:
            if not self.database:
                self.database = DAOTreasuryDatabase()
            
            # Простой запрос для проверки доступности
            stats = self.database.get_database_stats()
            
            return {
                'status': 'ok',
                'message': 'Database accessible',
                'stats': stats
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Database error: {str(e)}'
            }
    
    async def _check_activity_health(self) -> Dict[str, Any]:
        """Проверка последней активности мониторинга"""
        try:
            if not self.database:
                self.database = DAOTreasuryDatabase()
            
            # Проверяем последние транзакции и алерты
            recent_alerts = self.database.get_recent_alerts(hours=24)
            
            # Считаем активность за последние 2 часа
            two_hours_ago = datetime.now() - timedelta(hours=2)
            recent_activity = len([
                alert for alert in recent_alerts 
                if datetime.fromisoformat(alert['timestamp']) > two_hours_ago
            ])
            
            return {
                'status': 'ok',
                'message': f'Recent activity: {recent_activity} alerts in last 2h',
                'last_activity': self.last_activity_time.isoformat(),
                'alerts_24h': len(recent_alerts)
            }
            
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Activity check failed: {str(e)}'
            }
    
    async def _check_environment_health(self) -> Dict[str, Any]:
        """Проверка переменных окружения"""
        required_vars = [
            'HELIUS_API_KEY',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            return {
                'status': 'warning',
                'message': f'Missing environment variables: {", ".join(missing_vars)}'
            }
        
        return {
            'status': 'ok',
            'message': 'All required environment variables set'
        }
    
    async def _get_detailed_status(self) -> Dict[str, Any]:
        """Получение детального статуса системы"""
        if not self.database:
            self.database = DAOTreasuryDatabase()
        
        stats = self.database.get_database_stats()
        recent_alerts = self.database.get_recent_alerts(hours=24, limit=10)
        
        return {
            'system': {
                'uptime': time.time(),
                'timestamp': datetime.now().isoformat(),
                'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development')
            },
            'database': stats,
            'monitoring': {
                'alerts_last_24h': len(recent_alerts),
                'last_activity': self.last_activity_time.isoformat()
            },
            'recent_alerts': recent_alerts
        }
    
    async def _get_metrics(self) -> Dict[str, Any]:
        """Получение метрик для мониторинга"""
        if not self.database:
            self.database = DAOTreasuryDatabase()
        
        stats = self.database.get_database_stats()
        
        return {
            'treasury_transactions_total': stats.get('treasury_transactions', 0),
            'pool_activities_total': stats.get('pool_activities', 0),
            'alerts_total': stats.get('alerts', 0),
            'database_size_mb': stats.get('database_size_mb', 0),
            'uptime_seconds': time.time()
        }
    
    def update_activity_time(self):
        """Обновление времени последней активности"""
        self.last_activity_time = datetime.now()
    
    async def start_server(self):
        """Запуск health check сервера"""
        try:
            logger.info(f"🏥 Initializing health check server...")
            logger.info(f"   Host: 0.0.0.0")
            logger.info(f"   Port: {self.port}")
            logger.info(f"   Endpoints: /health, /status, /metrics")
            
            config = uvicorn.Config(
                app=self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)
            
            logger.info(f"✅ Health check server configured, starting...")
            await server.serve()
            
        except Exception as e:
            logger.error(f"❌ Health check server startup failed: {e}")
            import traceback
            logger.error(f"Health check startup traceback: {traceback.format_exc()}")
            raise

# Глобальный экземпляр для использования в main.py
health_server = HealthCheckServer()

def get_health_server() -> HealthCheckServer:
    """Получение экземпляра health check сервера"""
    return health_server

if __name__ == "__main__":
    asyncio.run(health_server.start_server()) 