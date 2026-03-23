import sqlite3
from pathlib import Path
from typing import Any

from config import DB_PATH
from database.schema import SCHEMA_SQL


class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._migrate_budgets_table(conn)
            self._seed_default_categories(conn)

    def _migrate_budgets_table(self, conn: sqlite3.Connection) -> None:
        cols = conn.execute("PRAGMA table_info(budgets)").fetchall()
        col_names = {c["name"] for c in cols}
        if "category_id" not in col_names:
            conn.execute("ALTER TABLE budgets ADD COLUMN category_id INTEGER")

    def _seed_default_categories(self, conn: sqlite3.Connection) -> None:
        users = conn.execute("SELECT id FROM users").fetchall()
        default_income = ["Wynagrodzenie", "Premia", "Inne"]
        default_expense = ["Jedzenie", "Transport", "Mieszkanie", "Rozrywka", "Zdrowie", "Inne"]
        for row in users:
            user_id = row["id"]
            for name in default_income:
                conn.execute(
                    "INSERT OR IGNORE INTO categories(user_id, name, type) VALUES (?, ?, 'income')",
                    (user_id, name),
                )
            for name in default_expense:
                conn.execute(
                    "INSERT OR IGNORE INTO categories(user_id, name, type) VALUES (?, ?, 'expense')",
                    (user_id, name),
                )

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self._connect() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(query, params).fetchall()
