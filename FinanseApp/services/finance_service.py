import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from database.db_manager import DatabaseManager


class FinanceService:
    INVESTMENT_TYPES = ["Lokata", "Akcje", "ETF", "Kryptowaluty", "Obligacje", "Złoto", "Inne"]

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_categories(self, user_id: int, category_type: str | None = None) -> list[dict[str, Any]]:
        if category_type:
            rows = self.db.fetchall(
                "SELECT * FROM categories WHERE user_id = ? AND type = ? ORDER BY name",
                (user_id, category_type),
            )
        else:
            rows = self.db.fetchall("SELECT * FROM categories WHERE user_id = ? ORDER BY type, name", (user_id,))
        return [dict(r) for r in rows]

    def add_category(self, user_id: int, name: str, category_type: str) -> None:
        self.db.execute(
            "INSERT INTO categories(user_id, name, type) VALUES (?, ?, ?)",
            (user_id, name.strip(), category_type),
        )

    def delete_category(self, category_id: int, user_id: int) -> None:
        self.db.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))

    def save_budget(self, user_id: int, month_key: str, amount: float) -> None:
        # Zachowane dla kompatybilności: budżet ogólny (bez kategorii).
        existing = self.db.fetchone(
            "SELECT id FROM budgets WHERE user_id = ? AND month_key = ? AND category_id IS NULL",
            (user_id, month_key),
        )
        if existing:
            self.db.execute("UPDATE budgets SET amount = ? WHERE id = ?", (amount, int(existing["id"])))
        else:
            self.db.execute(
                "INSERT INTO budgets(user_id, month_key, category_id, amount) VALUES (?, ?, NULL, ?)",
                (user_id, month_key, amount),
            )

    def get_budget(self, user_id: int, month_key: str) -> float:
        row = self.db.fetchone(
            "SELECT amount FROM budgets WHERE user_id = ? AND month_key = ? AND category_id IS NULL",
            (user_id, month_key),
        )
        return float(row["amount"]) if row else 0.0

    def save_category_budget(self, user_id: int, month_key: str, category_id: int, amount: float) -> None:
        if amount < 0:
            raise ValueError("Limit kategorii nie może być ujemny.")
        existing = self.db.fetchone(
            "SELECT id FROM budgets WHERE user_id = ? AND month_key = ? AND category_id = ?",
            (user_id, month_key, category_id),
        )
        if existing:
            self.db.execute("UPDATE budgets SET amount = ? WHERE id = ?", (amount, int(existing["id"])))
        else:
            self.db.execute(
                "INSERT INTO budgets(user_id, month_key, category_id, amount) VALUES (?, ?, ?, ?)",
                (user_id, month_key, category_id, amount),
            )

    def get_category_budgets(self, user_id: int, month_key: str) -> dict[int, float]:
        rows = self.db.fetchall(
            """
            SELECT category_id, amount
            FROM budgets
            WHERE user_id = ? AND month_key = ? AND category_id IS NOT NULL
            """,
            (user_id, month_key),
        )
        return {int(r["category_id"]): float(r["amount"]) for r in rows}

    def add_transaction(
        self,
        table: str,
        user_id: int,
        title: str,
        amount: float,
        txn_date: str,
        category_id: int | None,
        note: str = "",
    ) -> None:
        self._validate_table(table)
        datetime.strptime(txn_date, "%Y-%m-%d")
        self.db.execute(
            f"INSERT INTO {table}(user_id, category_id, title, amount, txn_date, note) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, category_id, title.strip(), amount, txn_date, note.strip()),
        )

    def update_transaction(
        self,
        table: str,
        txn_id: int,
        user_id: int,
        title: str,
        amount: float,
        txn_date: str,
        category_id: int | None,
        note: str = "",
    ) -> None:
        self._validate_table(table)
        datetime.strptime(txn_date, "%Y-%m-%d")
        self.db.execute(
            f"UPDATE {table} SET title = ?, amount = ?, txn_date = ?, category_id = ?, note = ? WHERE id = ? AND user_id = ?",
            (title.strip(), amount, txn_date, category_id, note.strip(), txn_id, user_id),
        )

    def delete_transaction(self, table: str, txn_id: int, user_id: int) -> None:
        self._validate_table(table)
        self.db.execute(f"DELETE FROM {table} WHERE id = ? AND user_id = ?", (txn_id, user_id))

    def list_transactions(self, table: str, user_id: int) -> list[dict[str, Any]]:
        self._validate_table(table)
        rows = self.db.fetchall(
            f"""
            SELECT t.id, t.title, t.amount, t.txn_date, t.note, c.name AS category_name, t.category_id
            FROM {table} t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.user_id = ?
            ORDER BY t.txn_date DESC, t.id DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in rows]

    def dashboard_totals(self, user_id: int) -> dict[str, float]:
        income = self.db.fetchone("SELECT COALESCE(SUM(amount), 0) AS total FROM incomes WHERE user_id = ?", (user_id,))
        expense = self.db.fetchone("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?", (user_id,))
        total_income = float(income["total"]) if income else 0.0
        total_expense = float(expense["total"]) if expense else 0.0
        return {
            "income": total_income,
            "expense": total_expense,
            "balance": total_income - total_expense,
        }

    def dashboard_totals_for_period(self, user_id: int, year: int, month: int) -> dict[str, float]:
        month_key = f"{year:04d}-{month:02d}"
        income = self.db.fetchone(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM incomes WHERE user_id = ? AND substr(txn_date, 1, 7) = ?",
            (user_id, month_key),
        )
        expense = self.db.fetchone(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? AND substr(txn_date, 1, 7) = ?",
            (user_id, month_key),
        )
        total_income = float(income["total"]) if income else 0.0
        total_expense = float(expense["total"]) if expense else 0.0
        return {"income": total_income, "expense": total_expense, "balance": total_income - total_expense}

    def monthly_budget_overview(self, user_id: int, year: int, month: int) -> dict[str, float]:
        month_key = f"{year:04d}-{month:02d}"
        totals = self.dashboard_totals_for_period(user_id, year, month)
        limits_sum = self.db.fetchone(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM budgets
            WHERE user_id = ? AND month_key = ? AND category_id IS NOT NULL
            """,
            (user_id, month_key),
        )
        planned = float(limits_sum["total"]) if limits_sum else 0.0
        income = totals["income"]
        expense = totals["expense"]
        return {
            "income": income,
            "expense": expense,
            "balance": totals["balance"],
            "planned_budget": planned,
            "unallocated_budget": income - planned,
            "spent_percent_of_income": round((expense / income) * 100, 2) if income > 0 else 0.0,
        }

    def expenses_by_category(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT COALESCE(c.name, 'Bez kategorii') AS category, COALESCE(SUM(e.amount), 0) AS total
            FROM expenses e
            LEFT JOIN categories c ON c.id = e.category_id
            WHERE e.user_id = ?
            GROUP BY COALESCE(c.name, 'Bez kategorii')
            ORDER BY total DESC
            """,
            (user_id,),
        )
        return [dict(r) for r in rows]

    def expenses_by_category_for_period(self, user_id: int, year: int, month: int) -> list[dict[str, Any]]:
        month_key = f"{year:04d}-{month:02d}"
        rows = self.db.fetchall(
            """
            SELECT COALESCE(c.name, 'Bez kategorii') AS category, COALESCE(SUM(e.amount), 0) AS total
            FROM expenses e
            LEFT JOIN categories c ON c.id = e.category_id
            WHERE e.user_id = ? AND substr(e.txn_date, 1, 7) = ?
            GROUP BY COALESCE(c.name, 'Bez kategorii')
            ORDER BY total DESC
            """,
            (user_id, month_key),
        )
        return [dict(r) for r in rows]

    def category_budget_status(self, user_id: int, year: int, month: int) -> list[dict[str, Any]]:
        month_key = f"{year:04d}-{month:02d}"
        expense_categories = self.list_categories(user_id, "expense")
        spent_rows = self.db.fetchall(
            """
            SELECT category_id, COALESCE(SUM(amount), 0) AS spent
            FROM expenses
            WHERE user_id = ? AND substr(txn_date, 1, 7) = ?
            GROUP BY category_id
            """,
            (user_id, month_key),
        )
        spent_map: dict[int, float] = {}
        for r in spent_rows:
            if r["category_id"] is not None:
                spent_map[int(r["category_id"])] = float(r["spent"])
        limits_map = self.get_category_budgets(user_id, month_key)
        result: list[dict[str, Any]] = []
        for cat in expense_categories:
            cid = int(cat["id"])
            limit = float(limits_map.get(cid, 0.0))
            spent = float(spent_map.get(cid, 0.0))
            usage = round((spent / limit) * 100, 2) if limit > 0 else 0.0
            status = "OK"
            if limit > 0 and usage >= 100:
                status = "Przekroczono"
            elif limit > 0 and usage >= 80:
                status = "Uwaga"
            result.append(
                {
                    "category_id": cid,
                    "category_name": cat["name"],
                    "limit": limit,
                    "spent": spent,
                    "usage_percent": usage,
                    "status": status,
                }
            )
        return result

    def monthly_ratio(self, user_id: int) -> dict[str, float]:
        month_key = datetime.now().strftime("%Y-%m")
        income = self.db.fetchone(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM incomes WHERE user_id = ? AND substr(txn_date, 1, 7) = ?",
            (user_id, month_key),
        )
        expense = self.db.fetchone(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? AND substr(txn_date, 1, 7) = ?",
            (user_id, month_key),
        )
        total_income = float(income["total"]) if income else 0.0
        total_expense = float(expense["total"]) if expense else 0.0
        budget = self.get_budget(user_id, month_key)
        if budget > 0 and total_expense > budget:
            self.db.execute(
                "INSERT INTO alerts(user_id, message, level) VALUES (?, ?, 'warning')",
                (user_id, f"Przekroczono budżet dla {month_key}."),
            )
        return {"month_income": total_income, "month_expense": total_expense, "budget": budget}

    def add_recurring_payment(self, user_id: int, name: str, amount: float, due_day: int) -> None:
        self.db.execute(
            "INSERT INTO recurring_payments(user_id, name, amount, due_day) VALUES (?, ?, ?, ?)",
            (user_id, name.strip(), amount, due_day),
        )

    def list_alerts(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall("SELECT * FROM alerts WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
        return [dict(r) for r in rows]

    def list_transactions_filtered(
        self,
        table: str,
        user_id: int,
        date_from: str = "",
        date_to: str = "",
        year: int | None = None,
        month: int | None = None,
        category_id: int | None = None,
        search_text: str = "",
    ) -> list[dict[str, Any]]:
        self._validate_table(table)
        query = [
            f"""
            SELECT t.id, t.title, t.amount, t.txn_date, t.note, c.name AS category_name, t.category_id
            FROM {table} t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.user_id = ?
            """
        ]
        params: list[Any] = [user_id]

        if date_from:
            datetime.strptime(date_from, "%Y-%m-%d")
            query.append("AND t.txn_date >= ?")
            params.append(date_from)
        if date_to:
            datetime.strptime(date_to, "%Y-%m-%d")
            query.append("AND t.txn_date <= ?")
            params.append(date_to)
        if year and month:
            query.append("AND substr(t.txn_date, 1, 7) = ?")
            params.append(f"{year:04d}-{month:02d}")
        if category_id:
            query.append("AND t.category_id = ?")
            params.append(category_id)
        if search_text.strip():
            query.append("AND (LOWER(t.title) LIKE ? OR LOWER(COALESCE(c.name, '')) LIKE ?)")
            term = f"%{search_text.strip().lower()}%"
            params.extend([term, term])

        query.append("ORDER BY t.txn_date DESC, t.id DESC")
        rows = self.db.fetchall(" ".join(query), tuple(params))
        return [dict(r) for r in rows]

    def list_history_filtered(
        self,
        user_id: int,
        txn_type: str = "all",
        date_from: str = "",
        date_to: str = "",
        year: int | None = None,
        month: int | None = None,
        category_id: int | None = None,
        search_text: str = "",
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if txn_type in {"all", "income"}:
            for row in self.list_transactions_filtered(
                "incomes", user_id, date_from, date_to, year, month, category_id, search_text
            ):
                row["type"] = "Przychód"
                rows.append(row)
        if txn_type in {"all", "expense"}:
            for row in self.list_transactions_filtered(
                "expenses", user_id, date_from, date_to, year, month, category_id, search_text
            ):
                row["type"] = "Wydatek"
                rows.append(row)
        rows.sort(key=lambda x: (x["txn_date"], x["id"]), reverse=True)
        return rows

    def import_transactions_from_csv(self, user_id: int, table: str, file_path: str) -> dict[str, Any]:
        self._validate_table(table)
        category_type = "income" if table == "incomes" else "expense"
        path = Path(file_path)
        if not path.exists():
            raise ValueError("Nie znaleziono pliku CSV.")

        imported = 0
        errors: list[str] = []

        with open(path, "r", encoding="utf-8-sig", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            required = {"date", "amount", "category", "description"}
            if not reader.fieldnames:
                raise ValueError("Plik CSV nie zawiera nagłówków.")
            normalized_headers = {name.strip().lower() for name in reader.fieldnames}
            if not required.issubset(normalized_headers):
                raise ValueError("Nieprawidłowe nagłówki CSV. Wymagane: date,amount,category,description")

            for idx, row in enumerate(reader, start=2):
                try:
                    txn_date = (row.get("date") or "").strip()
                    amount_raw = (row.get("amount") or "").strip()
                    category_name = (row.get("category") or "").strip()
                    description = (row.get("description") or "").strip()

                    if not txn_date:
                        raise ValueError("Brak daty.")
                    datetime.strptime(txn_date, "%Y-%m-%d")

                    if not amount_raw:
                        raise ValueError("Brak kwoty.")
                    amount = float(amount_raw.replace(",", "."))
                    if amount <= 0:
                        raise ValueError("Kwota musi być większa od zera.")

                    if not category_name:
                        raise ValueError("Brak kategorii.")
                    if not description:
                        raise ValueError("Brak opisu.")

                    category_id = self._get_or_create_category_id(user_id, category_name, category_type)
                    self.db.execute(
                        f"INSERT INTO {table}(user_id, category_id, title, amount, txn_date, note) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, category_id, description, round(amount, 2), txn_date, ""),
                    )
                    imported += 1
                except Exception as exc:
                    errors.append(f"Wiersz {idx}: {exc}")

        return {"imported": imported, "errors": errors}

    def add_investment(
        self,
        user_id: int,
        name: str,
        investment_type: str,
        purchase_date: str,
        invested_amount: float,
        current_value: float,
        notes: str = "",
    ) -> None:
        self._validate_investment_data(name, investment_type, purchase_date, invested_amount, current_value)
        self.db.execute(
            """
            INSERT INTO investments(user_id, name, investment_type, purchase_date, invested_amount, current_value, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name.strip(),
                investment_type,
                purchase_date,
                round(invested_amount, 2),
                round(current_value, 2),
                notes.strip(),
            ),
        )

    def update_investment(
        self,
        investment_id: int,
        user_id: int,
        name: str,
        investment_type: str,
        purchase_date: str,
        invested_amount: float,
        current_value: float,
        notes: str = "",
    ) -> None:
        self._validate_investment_data(name, investment_type, purchase_date, invested_amount, current_value)
        self.db.execute(
            """
            UPDATE investments
            SET name = ?, investment_type = ?, purchase_date = ?, invested_amount = ?, current_value = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                name.strip(),
                investment_type,
                purchase_date,
                round(invested_amount, 2),
                round(current_value, 2),
                notes.strip(),
                investment_id,
                user_id,
            ),
        )

    def delete_investment(self, investment_id: int, user_id: int) -> None:
        self.db.execute("DELETE FROM investments WHERE id = ? AND user_id = ?", (investment_id, user_id))

    def list_investments(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            """
            SELECT id, name, investment_type, purchase_date, invested_amount, current_value, notes, created_at
            FROM investments
            WHERE user_id = ?
            ORDER BY purchase_date DESC, id DESC
            """,
            (user_id,),
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            invested = float(item["invested_amount"])
            current = float(item["current_value"])
            profit_loss = round(current - invested, 2)
            roi = round((profit_loss / invested) * 100, 2) if invested > 0 else 0.0
            item["profit_loss"] = profit_loss
            item["roi_percent"] = roi
            result.append(item)
        return result

    def investments_summary(self, user_id: int) -> dict[str, float]:
        row = self.db.fetchone(
            """
            SELECT
                COALESCE(SUM(invested_amount), 0) AS total_invested,
                COALESCE(SUM(current_value), 0) AS total_current
            FROM investments
            WHERE user_id = ?
            """,
            (user_id,),
        )
        total_invested = float(row["total_invested"]) if row else 0.0
        total_current = float(row["total_current"]) if row else 0.0
        return {
            "total_invested": total_invested,
            "total_current": total_current,
            "total_profit_loss": round(total_current - total_invested, 2),
        }

    def generate_monthly_alerts(self, user_id: int, year: int, month: int) -> list[str]:
        alerts: list[str] = []
        month_key = f"{year:04d}-{month:02d}"
        overview = self.monthly_budget_overview(user_id, year, month)
        totals = self.dashboard_totals_for_period(user_id, year, month)
        category_status = self.category_budget_status(user_id, year, month)
        expenses_by_category = self.expenses_by_category_for_period(user_id, year, month)

        for row in category_status:
            if row["status"] == "Przekroczono":
                alerts.append(f"Przekroczono budżet kategorii: {row['category_name']}.")
            elif row["status"] == "Uwaga":
                alerts.append(f"Kategoria {row['category_name']} wykorzystała ponad 80% limitu.")

        if overview["unallocated_budget"] < 0:
            alerts.append("Zaplanowane wydatki przekraczają przychody.")

        if totals["expense"] > totals["income"] and (totals["expense"] > 0 or totals["income"] > 0):
            alerts.append("Wydatki są większe niż przychody w wybranym miesiącu.")

        # Prosta prognoza: wynik bieżący minus zaplanowane płatności cykliczne.
        recurring = self.db.fetchone(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM recurring_payments WHERE user_id = ? AND is_active = 1",
            (user_id,),
        )
        recurring_total = float(recurring["total"]) if recurring else 0.0
        forecast_balance = totals["balance"] - recurring_total
        if forecast_balance < 0:
            alerts.append("Prognozowane saldo po płatnościach cyklicznych jest ujemne.")

        today_day = datetime.now().day
        due_rows = self.db.fetchall(
            """
            SELECT name, due_day
            FROM recurring_payments
            WHERE user_id = ? AND is_active = 1 AND due_day BETWEEN ? AND ?
            ORDER BY due_day
            """,
            (user_id, today_day, min(today_day + 7, 31)),
        )
        for due in due_rows:
            alerts.append(f"Zbliża się płatność cykliczna: {due['name']} (dzień {due['due_day']}).")

        # Nietypowo wysoki wydatek = > 2x średniej wydatków w miesiącu.
        stats = self.db.fetchone(
            """
            SELECT COALESCE(AVG(amount), 0) AS avg_amount
            FROM expenses
            WHERE user_id = ? AND substr(txn_date, 1, 7) = ?
            """,
            (user_id, month_key),
        )
        avg_amount = float(stats["avg_amount"]) if stats else 0.0
        if avg_amount > 0:
            high = self.db.fetchone(
                """
                SELECT title, amount
                FROM expenses
                WHERE user_id = ? AND substr(txn_date, 1, 7) = ?
                ORDER BY amount DESC
                LIMIT 1
                """,
                (user_id, month_key),
            )
            if high and float(high["amount"]) > avg_amount * 2:
                alerts.append(f"Nietypowo wysoki wydatek: {high['title']} ({float(high['amount']):.2f} PLN).")

        # Prosty alert koncentracji wydatków: kategoria przekracza 40% całych wydatków.
        if totals["expense"] > 0 and expenses_by_category:
            top_cat = expenses_by_category[0]
            top_share = (float(top_cat["total"]) / totals["expense"]) * 100
            if top_share >= 40:
                alerts.append(f"Kategoria {top_cat['category']} przekroczyła 40% wydatków miesiąca.")

        return alerts

    def build_monthly_report(self, user_id: int, year: int, month: int) -> dict[str, Any]:
        month_key = f"{year:04d}-{month:02d}"
        overview = self.monthly_budget_overview(user_id, year, month)
        totals = self.dashboard_totals_for_period(user_id, year, month)
        expenses_by_category = self.expenses_by_category_for_period(user_id, year, month)
        category_budget_table = self.category_budget_status(user_id, year, month)
        alerts = self.generate_monthly_alerts(user_id, year, month)
        tx_count_row = self.db.fetchone(
            """
            SELECT
                (SELECT COUNT(1) FROM incomes WHERE user_id = ? AND substr(txn_date, 1, 7) = ?)
                +
                (SELECT COUNT(1) FROM expenses WHERE user_id = ? AND substr(txn_date, 1, 7) = ?) AS total
            """,
            (user_id, month_key, user_id, month_key),
        )
        tx_count = int(tx_count_row["total"]) if tx_count_row else 0
        top_categories = expenses_by_category[:3]
        budget_exceeded = any(row["status"] == "Przekroczono" for row in category_budget_table)
        top_text = top_categories[0]["category"] if top_categories else "brak danych"
        plus_minus = "plusie" if totals["balance"] >= 0 else "minusie"
        budget_text = "tak" if budget_exceeded else "nie"
        summary_text = (
            f"Najwięcej wydano na: {top_text}. "
            f"Miesiąc zakończył się na {plus_minus}. "
            f"Czy budżet został przekroczony: {budget_text}."
        )
        return {
            "month": month,
            "year": year,
            "totals": totals,
            "transaction_count": tx_count,
            "top_categories": top_categories,
            "budget": overview["planned_budget"],
            "budget_exceeded": budget_exceeded,
            "budget_table": category_budget_table,
            "unallocated_budget": overview["unallocated_budget"],
            "spent_percent_of_income": overview["spent_percent_of_income"],
            "alerts": alerts,
            "summary_text": summary_text,
        }

    def _ensure_category_ids(self, user_id: int, names: list[str], category_type: str) -> dict[str, int]:
        for name in names:
            self.db.execute(
                "INSERT OR IGNORE INTO categories(user_id, name, type) VALUES (?, ?, ?)",
                (user_id, name, category_type),
            )
        rows = self.db.fetchall(
            "SELECT id, name FROM categories WHERE user_id = ? AND type = ?",
            (user_id, category_type),
        )
        mapping = {row["name"]: int(row["id"]) for row in rows}
        return {name: mapping[name] for name in names}

    def _get_or_create_category_id(self, user_id: int, category_name: str, category_type: str) -> int:
        self.db.execute(
            "INSERT OR IGNORE INTO categories(user_id, name, type) VALUES (?, ?, ?)",
            (user_id, category_name, category_type),
        )
        row = self.db.fetchone(
            "SELECT id FROM categories WHERE user_id = ? AND name = ? AND type = ?",
            (user_id, category_name, category_type),
        )
        if not row:
            raise ValueError("Nie udało się utworzyć kategorii.")
        return int(row["id"])

    def _validate_investment_data(
        self,
        name: str,
        investment_type: str,
        purchase_date: str,
        invested_amount: float,
        current_value: float,
    ) -> None:
        if not name.strip():
            raise ValueError("Nazwa inwestycji jest wymagana.")
        if investment_type not in self.INVESTMENT_TYPES:
            raise ValueError("Nieprawidłowy typ inwestycji.")
        datetime.strptime(purchase_date, "%Y-%m-%d")
        if invested_amount <= 0:
            raise ValueError("Kwota zainwestowana musi być większa od zera.")
        if current_value < 0:
            raise ValueError("Wartość bieżąca nie może być ujemna.")

    @staticmethod
    def _validate_table(table: str) -> None:
        if table not in {"incomes", "expenses"}:
            raise ValueError("Nieprawidłowa tabela transakcji.")
