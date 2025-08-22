"""
Database Module

Database abstraction with connection pooling, transactions, and support for
PostgreSQL, MySQL, SQLite, and Google Cloud SQL.
"""

import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    from psycopg2.extras import RealDictCursor

    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False

try:
    import pymysql
    from pymysql import cursors

    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

try:
    from sqlalchemy import MetaData, Table, create_engine, text
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.pool import QueuePool

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from ..config import DatabaseConfig
from ..errors import ConfigurationError, DatabaseError
from ..logging import get_logger

logger = get_logger(__name__)


class DatabaseType(Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CLOUD_SQL_POSTGRES = "cloud_sql_postgres"
    CLOUD_SQL_MYSQL = "cloud_sql_mysql"


@dataclass
class QueryResult:
    """Query result with metadata."""

    rows: List[Dict[str, Any]]
    row_count: int
    execution_time: float
    columns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def first(self) -> Optional[Dict[str, Any]]:
        """Get first row."""
        return self.rows[0] if self.rows else None

    def all(self) -> List[Dict[str, Any]]:
        """Get all rows."""
        return self.rows


@dataclass
class TransactionResult:
    """Transaction execution result."""

    success: bool
    queries_executed: int
    execution_time: float
    error: Optional[str] = None


class Database(ABC):
    """Abstract database interface."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute a query and return results."""
        pass

    @abstractmethod
    def execute_non_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute a non-query (INSERT/UPDATE/DELETE) and return affected rows."""
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin a transaction."""
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    def get_connection(self):
        """Get raw database connection."""
        pass


class PostgreSQLDatabase(Database):
    """PostgreSQL database implementation."""

    def __init__(self, config: DatabaseConfig):
        if not HAS_POSTGRESQL:
            raise ConfigurationError("PostgreSQL library (psycopg2) not available")

        self.config = config
        self.connection = None
        self.connection_pool = None
        self._transaction_active = False
        self._lock = threading.Lock()

        # Create connection pool
        self._create_pool()

    def _create_pool(self):
        """Create PostgreSQL connection pool."""
        try:
            self.connection_pool = pg_pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.db_pool_size,
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
                sslmode=self.config.db_ssl_mode,
                cursor_factory=RealDictCursor,
            )
            logger.info(
                "Created PostgreSQL connection pool", pool_size=self.config.db_pool_size
            )
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}")
            raise DatabaseError(f"Connection pool creation failed: {e}")

    def connect(self) -> bool:
        """Get connection from pool."""
        try:
            with self._lock:
                if self.connection is None:
                    self.connection = self.connection_pool.getconn()
                    logger.debug("Acquired connection from PostgreSQL pool")
                return True
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL connection: {e}")
            return False

    def disconnect(self) -> None:
        """Return connection to pool."""
        try:
            with self._lock:
                if self.connection:
                    self.connection_pool.putconn(self.connection)
                    self.connection = None
                    logger.debug("Returned connection to PostgreSQL pool")
        except Exception as e:
            logger.error(f"Failed to return PostgreSQL connection: {e}")

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute query and return results."""
        start_time = time.time()

        try:
            if not self.connection:
                self.connect()

            with self.connection.cursor() as cursor:
                cursor.execute(query, params or {})
                rows = cursor.fetchall()
                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )

                # Convert RealDictRow to regular dict
                result_rows = [dict(row) for row in rows]

                execution_time = time.time() - start_time

                logger.debug(
                    "Executed PostgreSQL query",
                    query=query[:100],
                    row_count=len(result_rows),
                    execution_time=execution_time,
                )

                return QueryResult(
                    rows=result_rows,
                    row_count=len(result_rows),
                    execution_time=execution_time,
                    columns=columns,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"PostgreSQL query failed: {e}", query=query[:100])
            raise DatabaseError(f"Query execution failed: {e}", query=query)

    def execute_non_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute non-query and return affected rows."""
        try:
            if not self.connection:
                self.connect()

            with self.connection.cursor() as cursor:
                cursor.execute(query, params or {})
                affected_rows = cursor.rowcount

                if not self._transaction_active:
                    self.connection.commit()

                logger.debug(
                    "Executed PostgreSQL non-query",
                    query=query[:100],
                    affected_rows=affected_rows,
                )

                return affected_rows

        except Exception as e:
            if not self._transaction_active:
                self.connection.rollback()
            logger.error(f"PostgreSQL non-query failed: {e}", query=query[:100])
            raise DatabaseError(f"Non-query execution failed: {e}", query=query)

    def begin_transaction(self) -> None:
        """Begin transaction."""
        try:
            if not self.connection:
                self.connect()

            self._transaction_active = True
            logger.debug("Started PostgreSQL transaction")
        except Exception as e:
            logger.error(f"Failed to begin PostgreSQL transaction: {e}")
            raise DatabaseError(f"Transaction start failed: {e}")

    def commit_transaction(self) -> None:
        """Commit transaction."""
        try:
            if self.connection and self._transaction_active:
                self.connection.commit()
                self._transaction_active = False
                logger.debug("Committed PostgreSQL transaction")
        except Exception as e:
            logger.error(f"Failed to commit PostgreSQL transaction: {e}")
            raise DatabaseError(f"Transaction commit failed: {e}")

    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        try:
            if self.connection and self._transaction_active:
                self.connection.rollback()
                self._transaction_active = False
                logger.debug("Rolled back PostgreSQL transaction")
        except Exception as e:
            logger.error(f"Failed to rollback PostgreSQL transaction: {e}")
            raise DatabaseError(f"Transaction rollback failed: {e}")

    def get_connection(self):
        """Get raw connection."""
        if not self.connection:
            self.connect()
        return self.connection


class SQLiteDatabase(Database):
    """SQLite database implementation."""

    def __init__(self, database_path: str = ":memory:"):
        self.database_path = database_path
        self.connection = None
        self._transaction_active = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Connect to SQLite database."""
        try:
            with self._lock:
                if self.connection is None:
                    self.connection = sqlite3.connect(
                        self.database_path, check_same_thread=False
                    )
                    self.connection.row_factory = sqlite3.Row
                    logger.debug(f"Connected to SQLite database: {self.database_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from SQLite."""
        try:
            with self._lock:
                if self.connection:
                    self.connection.close()
                    self.connection = None
                    logger.debug("Disconnected from SQLite")
        except Exception as e:
            logger.error(f"Failed to disconnect from SQLite: {e}")

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute query and return results."""
        start_time = time.time()

        try:
            if not self.connection:
                self.connect()

            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            rows = cursor.fetchall()
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )

            # Convert sqlite3.Row to dict
            result_rows = [dict(row) for row in rows]

            execution_time = time.time() - start_time

            logger.debug(
                "Executed SQLite query",
                query=query[:100],
                row_count=len(result_rows),
                execution_time=execution_time,
            )

            return QueryResult(
                rows=result_rows,
                row_count=len(result_rows),
                execution_time=execution_time,
                columns=columns,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"SQLite query failed: {e}", query=query[:100])
            raise DatabaseError(f"Query execution failed: {e}", query=query)

    def execute_non_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute non-query and return affected rows."""
        try:
            if not self.connection:
                self.connect()

            cursor = self.connection.cursor()
            cursor.execute(query, params or {})
            affected_rows = cursor.rowcount

            if not self._transaction_active:
                self.connection.commit()

            logger.debug(
                "Executed SQLite non-query",
                query=query[:100],
                affected_rows=affected_rows,
            )

            return affected_rows

        except Exception as e:
            if not self._transaction_active:
                self.connection.rollback()
            logger.error(f"SQLite non-query failed: {e}", query=query[:100])
            raise DatabaseError(f"Non-query execution failed: {e}", query=query)

    def begin_transaction(self) -> None:
        """Begin transaction."""
        try:
            if not self.connection:
                self.connect()

            self.connection.execute("BEGIN")
            self._transaction_active = True
            logger.debug("Started SQLite transaction")
        except Exception as e:
            logger.error(f"Failed to begin SQLite transaction: {e}")
            raise DatabaseError(f"Transaction start failed: {e}")

    def commit_transaction(self) -> None:
        """Commit transaction."""
        try:
            if self.connection and self._transaction_active:
                self.connection.commit()
                self._transaction_active = False
                logger.debug("Committed SQLite transaction")
        except Exception as e:
            logger.error(f"Failed to commit SQLite transaction: {e}")
            raise DatabaseError(f"Transaction commit failed: {e}")

    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        try:
            if self.connection and self._transaction_active:
                self.connection.rollback()
                self._transaction_active = False
                logger.debug("Rolled back SQLite transaction")
        except Exception as e:
            logger.error(f"Failed to rollback SQLite transaction: {e}")
            raise DatabaseError(f"Transaction rollback failed: {e}")

    def get_connection(self):
        """Get raw connection."""
        if not self.connection:
            self.connect()
        return self.connection


class DatabaseManager:
    """
    High-level database management with connection pooling and transactions.
    """

    def __init__(self, database: Database):
        self.database = database
        self._query_cache: Dict[str, QueryResult] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_lock = threading.Lock()

    def _cache_key(self, query: str, params: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for query."""
        import hashlib

        content = f"{query}:{params or {}}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached result is still valid."""
        if key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[key] < self._cache_ttl

    def query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
    ) -> QueryResult:
        """Execute query with optional caching."""
        cache_key = None

        if use_cache:
            cache_key = self._cache_key(query, params)
            with self._cache_lock:
                if cache_key in self._query_cache and self._is_cache_valid(cache_key):
                    logger.debug(
                        "Returning cached query result", cache_key=cache_key[:8]
                    )
                    return self._query_cache[cache_key]

        result = self.database.execute_query(query, params)

        if use_cache and cache_key:
            with self._cache_lock:
                self._query_cache[cache_key] = result
                self._cache_timestamps[cache_key] = time.time()
                logger.debug("Cached query result", cache_key=cache_key[:8])

        return result

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Execute non-query."""
        return self.database.execute_non_query(query, params)

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert data into table."""
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]

        query = f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES ({", ".join(placeholders)})
        """

        return self.execute(query, data)

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where_clause: str,
        where_params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Update data in table."""
        set_clause = ", ".join([f"{col} = :{col}" for col in data.keys()])

        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        params = {**data, **(where_params or {})}
        return self.execute(query, params)

    def delete(
        self,
        table: str,
        where_clause: str,
        where_params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Delete data from table."""
        query = f"DELETE FROM {table} WHERE {where_clause}"
        return self.execute(query, where_params)

    def select(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        where_params: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        use_cache: bool = False,
    ) -> QueryResult:
        """Select data from table."""
        col_list = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_list} FROM {table}"

        if where_clause:
            query += f" WHERE {where_clause}"

        if order_by:
            query += f" ORDER BY {order_by}"

        if limit:
            query += f" LIMIT {limit}"

        return self.query(query, where_params, use_cache)

    @contextmanager
    def transaction(self):
        """Transaction context manager."""
        start_time = time.time()
        queries_executed = 0

        try:
            self.database.begin_transaction()
            yield self
            self.database.commit_transaction()

            execution_time = time.time() - start_time
            logger.info(
                "Transaction completed successfully",
                queries_executed=queries_executed,
                execution_time=execution_time,
            )

        except Exception as e:
            self.database.rollback_transaction()
            execution_time = time.time() - start_time
            logger.error(
                f"Transaction failed, rolled back: {e}",
                queries_executed=queries_executed,
                execution_time=execution_time,
            )
            raise

    def bulk_insert(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """Bulk insert data."""
        if not data_list:
            return 0

        total_inserted = 0

        with self.transaction():
            for data in data_list:
                total_inserted += self.insert(table, data)

        logger.info(f"Bulk inserted {total_inserted} rows into {table}")
        return total_inserted

    def execute_script(self, script: str) -> List[QueryResult]:
        """Execute multiple queries from script."""
        queries = [q.strip() for q in script.split(";") if q.strip()]
        results = []

        with self.transaction():
            for query in queries:
                if query.upper().startswith(("SELECT", "WITH")):
                    result = self.query(query)
                    results.append(result)
                else:
                    affected_rows = self.execute(query)
                    results.append(
                        QueryResult(
                            rows=[],
                            row_count=affected_rows,
                            execution_time=0,
                            columns=[],
                        )
                    )

        return results

    def clear_cache(self) -> None:
        """Clear query cache."""
        with self._cache_lock:
            self._query_cache.clear()
            self._cache_timestamps.clear()
            logger.info("Database query cache cleared")

    def close(self) -> None:
        """Close database connection."""
        self.database.disconnect()


def create_database(
    db_type: Union[str, DatabaseType], config: Optional[DatabaseConfig] = None, **kwargs
) -> DatabaseManager:
    """
    Factory function to create database instance.

    Args:
        db_type: Database type
        config: Database configuration
        **kwargs: Additional database-specific options

    Returns:
        DatabaseManager instance
    """
    if isinstance(db_type, str):
        db_type = DatabaseType(db_type.lower())

    if db_type == DatabaseType.POSTGRESQL:
        if config is None:
            raise ConfigurationError("DatabaseConfig required for PostgreSQL")
        database = PostgreSQLDatabase(config)
    elif db_type == DatabaseType.SQLITE:
        database_path = kwargs.get("database_path", ":memory:")
        database = SQLiteDatabase(database_path)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    return DatabaseManager(database)


# Connection helper functions
def get_database_url(config: DatabaseConfig, db_type: DatabaseType) -> str:
    """Get database connection URL."""
    if db_type == DatabaseType.POSTGRESQL:
        return f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"
    elif db_type == DatabaseType.MYSQL:
        return f"mysql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"
    else:
        raise ValueError(f"URL not supported for database type: {db_type}")


# Global database instance
_global_database = None


def get_database(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Get global database instance."""
    global _global_database
    if _global_database is None:
        if config is None:
            # Default to SQLite for development
            _global_database = create_database(DatabaseType.SQLITE)
        else:
            _global_database = create_database(DatabaseType.POSTGRESQL, config)
    return _global_database
