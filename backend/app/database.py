from __future__ import annotations

import os
import sqlite3
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol

from .demo_data import create_connection
from .sql_guard import validate_sql


Dialect = Literal["sqlite", "postgres"]


class ReadonlyDatabase(Protocol):
    dialect: Dialect

    def execute_readonly(self, sql: str) -> list[dict[str, Any]]:
        ...

    def ping(self) -> float:
        """Return round-trip latency in milliseconds, or raise on failure."""
        ...


class SQLiteDatabase:
    dialect: Dialect = "sqlite"

    def __init__(self, connection: sqlite3.Connection | None = None) -> None:
        self.connection = connection or create_connection()

    def execute_readonly(self, sql: str) -> list[dict[str, Any]]:
        guard = validate_sql(sql)
        if not guard.ok:
            raise ValueError("SQL bloque par le garde-fou.")

        cursor = self.connection.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

    def ping(self) -> float:
        t0 = time.perf_counter()
        self.connection.execute("SELECT 1")
        return (time.perf_counter() - t0) * 1000


class PostgresDatabase:
    dialect: Dialect = "postgres"

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def execute_readonly(self, sql: str) -> list[dict[str, Any]]:
        guard = validate_sql(sql)
        if not guard.ok:
            raise ValueError("SQL bloque par le garde-fou.")

        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("La dependance psycopg est requise pour PostgreSQL.") from exc

        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(sql)
                return [_jsonable_row(row) for row in cursor.fetchall()]

    def ping(self) -> float:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("La dependance psycopg est requise pour PostgreSQL.") from exc

        t0 = time.perf_counter()
        with psycopg.connect(self.database_url) as connection:
            connection.execute("SELECT 1")
        return (time.perf_counter() - t0) * 1000


def create_database_from_env() -> ReadonlyDatabase:
    database_url = os.getenv("FABRIQ_DATABASE_URL")
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        return PostgresDatabase(database_url)

    return SQLiteDatabase()


def _jsonable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable_value(value) for key, value in row.items()}


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value
