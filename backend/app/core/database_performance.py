"""
Database performance optimization utilities
"""
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from app.core.database import async_engine, sync_engine
from app.core.logging import get_logger
from app.core.monitoring import metrics_collector

# Performance logger
perf_logger = get_logger("database.performance")


class DatabasePerformanceMonitor:
    """Database performance monitoring and optimization"""
    
    def __init__(self):
        self.query_stats = {}
        self.slow_query_threshold = 1.0  # seconds
        self.connection_pool_stats = {}
        
    def setup_monitoring(self):
        """Setup database performance monitoring"""
        # Monitor query execution time
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            
        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            
            # Log slow queries
            if total_time > self.slow_query_threshold:
                perf_logger.warning(
                    f"Slow query detected: {total_time:.3f}s",
                    extra={
                        "query_time": total_time,
                        "statement": statement[:200],  # Truncate long queries
                        "parameters": str(parameters)[:100] if parameters else None
                    }
                )
            
            # Update query statistics
            query_hash = hash(statement)
            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = {
                    "statement": statement[:100],
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "max_time": 0,
                    "min_time": float('inf')
                }
            
            stats = self.query_stats[query_hash]
            stats["count"] += 1
            stats["total_time"] += total_time
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["max_time"] = max(stats["max_time"], total_time)
            stats["min_time"] = min(stats["min_time"], total_time)
            
            # Send metrics to monitoring system
            metrics_collector.record_histogram(
                "database_query_duration",
                total_time,
                tags={"query_type": self._get_query_type(statement)}
            )
        
        # Monitor connection pool
        @event.listens_for(Pool, "connect")
        def receive_connect(dbapi_connection, connection_record):
            metrics_collector.increment_counter("database_connections_created")
            
        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            metrics_collector.increment_counter("database_connections_checked_out")
            
        @event.listens_for(Pool, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            metrics_collector.increment_counter("database_connections_checked_in")
    
    def _get_query_type(self, statement: str) -> str:
        """Determine query type from SQL statement"""
        statement_upper = statement.upper().strip()
        if statement_upper.startswith("SELECT"):
            return "SELECT"
        elif statement_upper.startswith("INSERT"):
            return "INSERT"
        elif statement_upper.startswith("UPDATE"):
            return "UPDATE"
        elif statement_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "OTHER"
    
    async def get_query_statistics(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        return {
            "total_queries": len(self.query_stats),
            "slow_queries": sum(1 for stats in self.query_stats.values() 
                              if stats["avg_time"] > self.slow_query_threshold),
            "top_slow_queries": sorted(
                self.query_stats.values(),
                key=lambda x: x["avg_time"],
                reverse=True
            )[:10],
            "query_type_distribution": self._get_query_type_distribution()
        }
    
    def _get_query_type_distribution(self) -> Dict[str, int]:
        """Get distribution of query types"""
        distribution = {}
        for stats in self.query_stats.values():
            query_type = self._get_query_type(stats["statement"])
            distribution[query_type] = distribution.get(query_type, 0) + stats["count"]
        return distribution
    
    async def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool = async_engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in_connections": pool.checkedin(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "invalid_connections": pool.invalid(),
        }


class DatabaseHealthChecker:
    """Database health monitoring"""
    
    def __init__(self):
        self.health_checks = []
        
    async def check_database_health(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        # Connection test
        try:
            connection_start = time.time()
            async with async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            connection_time = time.time() - connection_start
            
            health_status["checks"]["connection"] = {
                "status": "healthy",
                "response_time": connection_time,
                "message": "Database connection successful"
            }
            
            if connection_time > 1.0:
                health_status["checks"]["connection"]["status"] = "warning"
                health_status["checks"]["connection"]["message"] = "Slow database connection"
                
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["connection"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
        
        # Connection pool health
        try:
            pool_stats = await DatabasePerformanceMonitor().get_connection_pool_stats()
            pool_utilization = (pool_stats["checked_out_connections"] / 
                              (pool_stats["pool_size"] + pool_stats["overflow_connections"])) * 100
            
            health_status["checks"]["connection_pool"] = {
                "status": "healthy" if pool_utilization < 80 else "warning",
                "utilization_percent": pool_utilization,
                "stats": pool_stats
            }
            
            if pool_utilization >= 90:
                health_status["checks"]["connection_pool"]["status"] = "critical"
                health_status["status"] = "degraded"
                
        except Exception as e:
            health_status["checks"]["connection_pool"] = {
                "status": "error",
                "message": f"Failed to get pool stats: {str(e)}"
            }
        
        # Disk space check (if applicable)
        try:
            async with async_engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        pg_size_pretty(pg_total_relation_size('pg_class')) as system_size
                """))
                row = result.fetchone()
                
                health_status["checks"]["storage"] = {
                    "status": "healthy",
                    "database_size": row[0] if row else "unknown",
                    "system_size": row[1] if row else "unknown"
                }
                
        except Exception as e:
            health_status["checks"]["storage"] = {
                "status": "warning",
                "message": f"Could not check storage: {str(e)}"
            }
        
        # Performance metrics
        try:
            perf_monitor = DatabasePerformanceMonitor()
            query_stats = await perf_monitor.get_query_statistics()
            
            health_status["checks"]["performance"] = {
                "status": "healthy" if query_stats["slow_queries"] < 10 else "warning",
                "slow_queries_count": query_stats["slow_queries"],
                "total_queries": query_stats["total_queries"]
            }
            
        except Exception as e:
            health_status["checks"]["performance"] = {
                "status": "error",
                "message": f"Performance check failed: {str(e)}"
            }
        
        return health_status


class DatabaseOptimizer:
    """Database optimization utilities"""
    
    @staticmethod
    async def create_performance_indexes():
        """Create performance-optimized indexes"""
        indexes = [
            # User table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at)",
            
            # Company table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_symbol ON companies(symbol)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_sector ON companies(sector)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_market_cap ON companies(market_cap)",
            
            # Market data indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_company_date ON market_data(company_id, price_date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_date ON market_data(price_date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_volume ON market_data(volume) WHERE volume > 0",
            
            # Financial statements indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_statements_company_period ON financial_statements(company_id, period_end_date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_financial_statements_type ON financial_statements(statement_type)",
            
            # Portfolio indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolios_user ON portfolios(user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolios_active ON portfolios(is_active) WHERE is_active = true",
            
            # Transaction indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_portfolio ON transactions(portfolio_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_date ON transactions(transaction_date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_type ON transactions(transaction_type)",
            
            # Audit log indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)",
            
            # Session indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_token ON user_sessions(token_hash)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active) WHERE is_active = true",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at)",
        ]
        
        try:
            async with async_engine.begin() as conn:
                for index_sql in indexes:
                    try:
                        await conn.execute(text(index_sql))
                        perf_logger.info(f"Created index: {index_sql}")
                    except Exception as e:
                        perf_logger.warning(f"Failed to create index: {index_sql}, Error: {str(e)}")
                        
        except Exception as e:
            perf_logger.error(f"Failed to create performance indexes: {str(e)}")
    
    @staticmethod
    async def analyze_table_statistics():
        """Update table statistics for query optimization"""
        try:
            async with async_engine.begin() as conn:
                # Update statistics for all tables
                await conn.execute(text("ANALYZE"))
                perf_logger.info("Updated table statistics for query optimization")
                
        except Exception as e:
            perf_logger.error(f"Failed to analyze table statistics: {str(e)}")
    
    @staticmethod
    async def vacuum_tables():
        """Vacuum tables to reclaim space and update statistics"""
        try:
            # Note: VACUUM cannot be run inside a transaction
            async with async_engine.connect() as conn:
                await conn.execute(text("VACUUM ANALYZE"))
                perf_logger.info("Completed VACUUM ANALYZE operation")
                
        except Exception as e:
            perf_logger.error(f"Failed to vacuum tables: {str(e)}")


# Global instances
db_performance_monitor = DatabasePerformanceMonitor()
db_health_checker = DatabaseHealthChecker()
db_optimizer = DatabaseOptimizer()


# Context manager for query performance tracking
@asynccontextmanager
async def track_query_performance(query_name: str):
    """Context manager to track individual query performance"""
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        metrics_collector.record_histogram(
            "custom_query_duration",
            execution_time,
            tags={"query_name": query_name}
        )
        
        if execution_time > 1.0:  # Log slow queries
            perf_logger.warning(
                f"Slow custom query: {query_name} took {execution_time:.3f}s"
            )


# Initialization function
async def initialize_database_performance():
    """Initialize database performance monitoring"""
    try:
        # Setup monitoring
        db_performance_monitor.setup_monitoring()
        
        # Create performance indexes
        await db_optimizer.create_performance_indexes()
        
        # Update table statistics
        await db_optimizer.analyze_table_statistics()
        
        perf_logger.info("Database performance optimization initialized")
        
    except Exception as e:
        perf_logger.error(f"Failed to initialize database performance: {str(e)}")
