from datetime import datetime
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.auth_service import AuthService
from services.export_service import ExportService
from services.finance_service import FinanceService
from services.gemini_service import GeminiService
from utils.validators import parse_amount


class TransactionDialog(QDialog):
    def __init__(self, categories: list[dict], title: str, data: dict | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(360, 220)
        self.result_data: dict | None = None
        form = QFormLayout(self)
        self.title_edit = QLineEdit(data["title"] if data else "")
        self.amount_edit = QLineEdit(str(data["amount"]) if data else "")
        self.date_edit = QLineEdit(data["txn_date"] if data else datetime.now().strftime("%Y-%m-%d"))
        self.note_edit = QLineEdit(data["note"] if data else "")
        self.category = QComboBox()
        self.category.addItem("Bez kategorii", None)
        for c in categories:
            self.category.addItem(c["name"], c["id"])
        if data and data.get("category_id"):
            idx = self.category.findData(data["category_id"])
            if idx >= 0:
                self.category.setCurrentIndex(idx)
        form.addRow("Tytuł:", self.title_edit)
        form.addRow("Kwota:", self.amount_edit)
        form.addRow("Data (YYYY-MM-DD):", self.date_edit)
        form.addRow("Kategoria:", self.category)
        form.addRow("Notatka:", self.note_edit)
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self._save)
        form.addRow(save_btn)

    def _save(self) -> None:
        try:
            if not self.title_edit.text().strip():
                raise ValueError("Tytuł jest wymagany.")
            self.result_data = {
                "title": self.title_edit.text().strip(),
                "amount": parse_amount(self.amount_edit.text()),
                "txn_date": self.date_edit.text().strip(),
                "category_id": self.category.currentData(),
                "note": self.note_edit.text().strip(),
            }
            datetime.strptime(self.result_data["txn_date"], "%Y-%m-%d")
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Błąd formularza", str(exc))


class InvestmentDialog(QDialog):
    def __init__(
        self,
        investment_types: list[str],
        title: str,
        data: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 280)
        self.result_data: dict | None = None
        form = QFormLayout(self)
        self.name_edit = QLineEdit(data["name"] if data else "")
        self.type_combo = QComboBox()
        self.type_combo.addItems(investment_types)
        if data:
            idx = self.type_combo.findText(data["investment_type"])
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
        self.purchase_date_edit = QLineEdit(data["purchase_date"] if data else datetime.now().strftime("%Y-%m-%d"))
        self.invested_edit = QLineEdit(str(data["invested_amount"]) if data else "")
        self.current_edit = QLineEdit(str(data["current_value"]) if data else "0")
        self.notes_edit = QLineEdit(data["notes"] if data else "")
        form.addRow("Nazwa:", self.name_edit)
        form.addRow("Typ:", self.type_combo)
        form.addRow("Data zakupu (YYYY-MM-DD):", self.purchase_date_edit)
        form.addRow("Kwota zainwestowana:", self.invested_edit)
        form.addRow("Wartość bieżąca:", self.current_edit)
        form.addRow("Notatki:", self.notes_edit)
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self._save)
        form.addRow(save_btn)

    def _save(self) -> None:
        try:
            name = self.name_edit.text().strip()
            if not name:
                raise ValueError("Nazwa inwestycji jest wymagana.")
            purchase_date = self.purchase_date_edit.text().strip()
            datetime.strptime(purchase_date, "%Y-%m-%d")
            invested = float(self.invested_edit.text().replace(",", "."))
            current = float(self.current_edit.text().replace(",", "."))
            if invested <= 0:
                raise ValueError("Kwota zainwestowana musi być większa od zera.")
            if current < 0:
                raise ValueError("Wartość bieżąca nie może być ujemna.")
            self.result_data = {
                "name": name,
                "investment_type": self.type_combo.currentText(),
                "purchase_date": purchase_date,
                "invested_amount": round(invested, 2),
                "current_value": round(current, 2),
                "notes": self.notes_edit.text().strip(),
            }
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Błąd formularza", str(exc))


class MainWindow(QMainWindow):
    def __init__(self, auth_service: AuthService, finance_service: FinanceService, gemini_service: GeminiService) -> None:
        super().__init__()
        self.auth_service = auth_service
        self.finance_service = finance_service
        self.gemini_service = gemini_service
        self.user_id: int | None = None
        now = datetime.now()
        self.selected_year = now.year
        self.selected_month = now.month
        self.setWindowTitle("FinanseApp")
        self.resize(1000, 700)
        self._build_ui()

    def set_user(self, user_id: int) -> None:
        self.user_id = user_id

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.dashboard_tab = self._build_dashboard_tab()
        self.profile_tab = self._build_profile_tab()
        self.incomes_tab = self._build_transactions_tab("incomes", "Przychody")
        self.expenses_tab = self._build_transactions_tab("expenses", "Wydatki")
        self.history_tab = self._build_history_tab()
        self.categories_tab = self._build_categories_tab()
        self.investments_tab = self._build_investments_tab()
        self.reports_tab = self._build_reports_tab()
        self.ai_tab = self._build_ai_tab()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.profile_tab, "Profil")
        self.tabs.addTab(self.incomes_tab, "Przychody")
        self.tabs.addTab(self.expenses_tab, "Wydatki")
        self.tabs.addTab(self.history_tab, "Historia")
        self.tabs.addTab(self.categories_tab, "Kategorie")
        self.tabs.addTab(self.investments_tab, "Inwestycje")
        self.tabs.addTab(self.reports_tab, "Raporty")
        self.tabs.addTab(self.ai_tab, "Analiza AI")

    def _build_dashboard_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)

        period_row = QHBoxLayout()
        self.month_selector = QComboBox()
        self.month_selector.addItems([f"{i:02d}" for i in range(1, 13)])
        self.month_selector.setCurrentIndex(self.selected_month - 1)
        self.year_selector = QComboBox()
        years = [str(y) for y in range(datetime.now().year - 5, datetime.now().year + 2)]
        self.year_selector.addItems(years)
        self.year_selector.setCurrentText(str(self.selected_year))
        apply_period_btn = QPushButton("Zastosuj okres")
        apply_period_btn.clicked.connect(self._on_period_change)
        period_row.addWidget(QLabel("Miesiąc:"))
        period_row.addWidget(self.month_selector)
        period_row.addWidget(QLabel("Rok:"))
        period_row.addWidget(self.year_selector)
        period_row.addWidget(apply_period_btn)
        lay.addLayout(period_row)

        cards = QGridLayout()
        self.total_income_lbl = QLabel("0.00 PLN")
        self.total_expense_lbl = QLabel("0.00 PLN")
        self.balance_lbl = QLabel("0.00 PLN")
        self.planned_budget_lbl = QLabel("0.00 PLN")
        self.unallocated_budget_lbl = QLabel("0.00 PLN")
        self.spent_percent_lbl = QLabel("0.00%")
        cards.addWidget(QLabel("Suma przychodów"), 0, 0)
        cards.addWidget(self.total_income_lbl, 0, 1)
        cards.addWidget(QLabel("Suma wydatków"), 1, 0)
        cards.addWidget(self.total_expense_lbl, 1, 1)
        cards.addWidget(QLabel("Bieżące saldo"), 2, 0)
        cards.addWidget(self.balance_lbl, 2, 1)
        cards.addWidget(QLabel("Budżet zaplanowany"), 3, 0)
        cards.addWidget(self.planned_budget_lbl, 3, 1)
        cards.addWidget(QLabel("Pozostało do zaplanowania"), 4, 0)
        cards.addWidget(self.unallocated_budget_lbl, 4, 1)
        cards.addWidget(QLabel("Wydano % przychodu"), 5, 0)
        cards.addWidget(self.spent_percent_lbl, 5, 1)
        lay.addLayout(cards)

        budget_row = QHBoxLayout()
        self.budget_category_selector = QComboBox()
        self.budget_input = QLineEdit("0")
        self.budget_save_btn = QPushButton("Zapisz limit kategorii")
        self.budget_save_btn.clicked.connect(self._save_budget)
        budget_row.addWidget(QLabel("Kategoria:"))
        budget_row.addWidget(self.budget_category_selector)
        budget_row.addWidget(QLabel("Limit:"))
        budget_row.addWidget(self.budget_input)
        budget_row.addWidget(self.budget_save_btn)
        lay.addLayout(budget_row)

        self.category_budget_table = QTableWidget(0, 5)
        self.category_budget_table.setHorizontalHeaderLabels(["Kategoria", "Limit", "Wydano", "% wykorzystania", "Status"])
        lay.addWidget(QLabel("Budżet kategorii"))
        lay.addWidget(self.category_budget_table)

        self.alerts_box = QTextEdit()
        self.alerts_box.setReadOnly(True)
        lay.addWidget(QLabel("Alerty"))
        lay.addWidget(self.alerts_box)

        self.monthly_report_box = QTextEdit()
        self.monthly_report_box.setReadOnly(True)
        lay.addWidget(QLabel("Raport miesięczny"))
        lay.addWidget(self.monthly_report_box)

        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        lay.addWidget(self.canvas)
        return widget

    def _build_profile_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.p_first_name = QLineEdit()
        self.p_last_name = QLineEdit()
        self.p_income = QLineEdit()
        self.p_rent = QLineEdit()
        self.p_goal = QLineEdit()
        self.p_password = QLineEdit()
        self.p_password.setPlaceholderText("Nowe hasło (opcjonalnie)")
        self.profile_save_btn = QPushButton("Zapisz profil")
        self.profile_save_btn.clicked.connect(self._save_profile)
        form.addRow("Imię:", self.p_first_name)
        form.addRow("Nazwisko:", self.p_last_name)
        form.addRow("Miesięczny dochód:", self.p_income)
        form.addRow("Czynsz:", self.p_rent)
        form.addRow("Cel oszczędności:", self.p_goal)
        form.addRow("Nowe hasło:", self.p_password)
        form.addRow(self.profile_save_btn)
        return widget

    def _build_transactions_tab(self, table: str, title: str) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        filter_row = QHBoxLayout()
        date_from = QLineEdit()
        date_to = QLineEdit()
        search = QLineEdit()
        category = QComboBox()
        category.addItem("Wszystkie", None)
        apply_btn = QPushButton("Filtruj")
        reset_btn = QPushButton("Reset")
        filter_row.addWidget(QLabel("Od:"))
        filter_row.addWidget(date_from)
        filter_row.addWidget(QLabel("Do:"))
        filter_row.addWidget(date_to)
        filter_row.addWidget(QLabel("Kategoria:"))
        filter_row.addWidget(category)
        filter_row.addWidget(QLabel("Szukaj:"))
        filter_row.addWidget(search)
        filter_row.addWidget(apply_btn)
        filter_row.addWidget(reset_btn)
        lay.addLayout(filter_row)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(f"Dodaj {title[:-1]}")
        edit_btn = QPushButton("Edytuj")
        del_btn = QPushButton("Usuń")
        add_btn.clicked.connect(lambda: self._add_transaction(table))
        edit_btn.clicked.connect(lambda: self._edit_transaction(table))
        del_btn.clicked.connect(lambda: self._delete_transaction(table))
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        lay.addLayout(btn_row)

        tbl = QTableWidget(0, 6)
        tbl.setHorizontalHeaderLabels(["ID", "Tytuł", "Kwota", "Data", "Kategoria", "Notatka"])
        tbl.setColumnHidden(0, True)
        lay.addWidget(tbl)
        if table == "incomes":
            self.incomes_table = tbl
            self.incomes_filter_from = date_from
            self.incomes_filter_to = date_to
            self.incomes_filter_search = search
            self.incomes_filter_category = category
            apply_btn.clicked.connect(lambda: self._refresh_transactions("incomes"))
            reset_btn.clicked.connect(lambda: self._reset_transaction_filters("incomes"))
        else:
            self.expenses_table = tbl
            self.expenses_filter_from = date_from
            self.expenses_filter_to = date_to
            self.expenses_filter_search = search
            self.expenses_filter_category = category
            apply_btn.clicked.connect(lambda: self._refresh_transactions("expenses"))
            reset_btn.clicked.connect(lambda: self._reset_transaction_filters("expenses"))
        return widget

    def _build_history_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.history_type = QComboBox()
        self.history_type.addItem("Wszystkie", "all")
        self.history_type.addItem("Przychody", "income")
        self.history_type.addItem("Wydatki", "expense")
        self.history_from = QLineEdit()
        self.history_to = QLineEdit()
        self.history_month = QComboBox()
        self.history_month.addItem("Wszystkie", None)
        self.history_month.addItems([f"{i:02d}" for i in range(1, 13)])
        self.history_month.setCurrentIndex(self.selected_month)
        self.history_year = QComboBox()
        self.history_year.addItem("Wszystkie", None)
        self.history_year.addItems([str(y) for y in range(datetime.now().year - 5, datetime.now().year + 2)])
        year_idx = self.history_year.findText(str(self.selected_year))
        if year_idx >= 0:
            self.history_year.setCurrentIndex(year_idx)
        self.history_category = QComboBox()
        self.history_category.addItem("Wszystkie", None)
        self.history_search = QLineEdit()
        apply_btn = QPushButton("Filtruj historię")
        reset_btn = QPushButton("Reset")
        apply_btn.clicked.connect(self._refresh_history)
        reset_btn.clicked.connect(self._reset_history_filters)
        row.addWidget(QLabel("Typ:"))
        row.addWidget(self.history_type)
        row.addWidget(QLabel("Od:"))
        row.addWidget(self.history_from)
        row.addWidget(QLabel("Do:"))
        row.addWidget(self.history_to)
        row.addWidget(QLabel("Miesiąc:"))
        row.addWidget(self.history_month)
        row.addWidget(QLabel("Rok:"))
        row.addWidget(self.history_year)
        row.addWidget(QLabel("Kategoria:"))
        row.addWidget(self.history_category)
        row.addWidget(QLabel("Szukaj:"))
        row.addWidget(self.history_search)
        row.addWidget(apply_btn)
        row.addWidget(reset_btn)
        lay.addLayout(row)
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(["ID", "Typ", "Tytuł", "Kwota", "Data", "Kategoria", "Notatka"])
        self.history_table.setColumnHidden(0, True)
        lay.addWidget(self.history_table)
        return widget

    def _build_categories_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.category_name = QLineEdit()
        self.category_type = QComboBox()
        self.category_type.addItems(["income", "expense"])
        add_btn = QPushButton("Dodaj kategorię")
        del_btn = QPushButton("Usuń zaznaczoną")
        add_btn.clicked.connect(self._add_category)
        del_btn.clicked.connect(self._delete_category)
        row.addWidget(QLabel("Nazwa:"))
        row.addWidget(self.category_name)
        row.addWidget(QLabel("Typ:"))
        row.addWidget(self.category_type)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lay.addLayout(row)
        self.categories_table = QTableWidget(0, 3)
        self.categories_table.setHorizontalHeaderLabels(["ID", "Nazwa", "Typ"])
        self.categories_table.setColumnHidden(0, True)
        lay.addWidget(self.categories_table)
        return widget

    def _build_investments_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)

        summary = QGridLayout()
        self.inv_total_invested_lbl = QLabel("0.00 PLN")
        self.inv_total_current_lbl = QLabel("0.00 PLN")
        self.inv_total_profit_lbl = QLabel("0.00 PLN")
        summary.addWidget(QLabel("Suma zainwestowanych środków"), 0, 0)
        summary.addWidget(self.inv_total_invested_lbl, 0, 1)
        summary.addWidget(QLabel("Suma aktualnej wartości"), 1, 0)
        summary.addWidget(self.inv_total_current_lbl, 1, 1)
        summary.addWidget(QLabel("Łączny zysk/strata"), 2, 0)
        summary.addWidget(self.inv_total_profit_lbl, 2, 1)
        lay.addLayout(summary)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Dodaj inwestycję")
        edit_btn = QPushButton("Edytuj")
        del_btn = QPushButton("Usuń")
        add_btn.clicked.connect(self._add_investment)
        edit_btn.clicked.connect(self._edit_investment)
        del_btn.clicked.connect(self._delete_investment)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        lay.addLayout(btn_row)

        self.investments_table = QTableWidget(0, 9)
        self.investments_table.setHorizontalHeaderLabels(
            ["ID", "Nazwa", "Typ", "Data zakupu", "Kwota", "Wartość", "Zysk/Strata", "Zwrot %", "Notatki"]
        )
        self.investments_table.setColumnHidden(0, True)
        lay.addWidget(self.investments_table)
        return widget

    def _build_reports_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        csv_btn = QPushButton("Eksport CSV")
        pdf_btn = QPushButton("Eksport PDF")
        import_incomes_btn = QPushButton("Import przychodów z CSV")
        import_expenses_btn = QPushButton("Import wydatków z CSV")
        csv_btn.clicked.connect(self._export_csv)
        pdf_btn.clicked.connect(self._export_pdf)
        import_incomes_btn.clicked.connect(lambda: self._import_csv("incomes"))
        import_expenses_btn.clicked.connect(lambda: self._import_csv("expenses"))
        lay.addWidget(csv_btn)
        lay.addWidget(pdf_btn)
        lay.addWidget(import_incomes_btn)
        lay.addWidget(import_expenses_btn)
        return widget

    def _build_ai_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        self.ai_status = QLabel("AI gotowe")
        self.ai_text = QTextEdit()
        self.ai_text.setReadOnly(True)
        run_ai_btn = QPushButton("Generuj analizę AI")
        run_ai_btn.clicked.connect(self._run_ai)
        lay.addWidget(self.ai_status)
        lay.addWidget(run_ai_btn)
        lay.addWidget(self.ai_text)
        return widget

    def refresh_all(self) -> None:
        if not self.user_id:
            return
        self._refresh_profile()
        self._refresh_filter_categories()
        self._refresh_transactions("incomes")
        self._refresh_transactions("expenses")
        self._refresh_categories()
        self._refresh_investments()
        self._refresh_history()
        self._refresh_dashboard()

    def _refresh_profile(self) -> None:
        user = self.auth_service.get_user(self.user_id)
        self.p_first_name.setText(user["first_name"])
        self.p_last_name.setText(user["last_name"])
        self.p_income.setText(str(user["monthly_income"]))
        self.p_rent.setText(str(user["rent"]))
        self.p_goal.setText(str(user["savings_goal"]))
        self.p_password.clear()

    def _refresh_filter_categories(self) -> None:
        income_categories = self.finance_service.list_categories(self.user_id, "income")
        expense_categories = self.finance_service.list_categories(self.user_id, "expense")
        all_categories = self.finance_service.list_categories(self.user_id)

        self.incomes_filter_category.clear()
        self.incomes_filter_category.addItem("Wszystkie", None)
        for c in income_categories:
            self.incomes_filter_category.addItem(c["name"], c["id"])

        self.expenses_filter_category.clear()
        self.expenses_filter_category.addItem("Wszystkie", None)
        for c in expense_categories:
            self.expenses_filter_category.addItem(c["name"], c["id"])

        self.history_category.clear()
        self.history_category.addItem("Wszystkie", None)
        for c in all_categories:
            self.history_category.addItem(c["name"], c["id"])

        current_category_id = self.budget_category_selector.currentData()
        self.budget_category_selector.clear()
        for c in expense_categories:
            self.budget_category_selector.addItem(c["name"], c["id"])
        if current_category_id is not None:
            idx = self.budget_category_selector.findData(current_category_id)
            if idx >= 0:
                self.budget_category_selector.setCurrentIndex(idx)

    def _refresh_transactions(self, table: str) -> None:
        if table == "incomes":
            date_from = self.incomes_filter_from.text().strip()
            date_to = self.incomes_filter_to.text().strip()
            search = self.incomes_filter_search.text().strip()
            category_id = self.incomes_filter_category.currentData()
        else:
            date_from = self.expenses_filter_from.text().strip()
            date_to = self.expenses_filter_to.text().strip()
            search = self.expenses_filter_search.text().strip()
            category_id = self.expenses_filter_category.currentData()

        data = self.finance_service.list_transactions_filtered(
            table,
            self.user_id,
            date_from=date_from,
            date_to=date_to,
            year=self.selected_year if not date_from and not date_to else None,
            month=self.selected_month if not date_from and not date_to else None,
            category_id=category_id,
            search_text=search,
        )
        tbl = self.incomes_table if table == "incomes" else self.expenses_table
        tbl.setRowCount(len(data))
        for i, row in enumerate(data):
            tbl.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            tbl.setItem(i, 1, QTableWidgetItem(row["title"]))
            tbl.setItem(i, 2, QTableWidgetItem(f"{float(row['amount']):.2f}"))
            tbl.setItem(i, 3, QTableWidgetItem(row["txn_date"]))
            tbl.setItem(i, 4, QTableWidgetItem(row["category_name"] or ""))
            tbl.setItem(i, 5, QTableWidgetItem(row["note"] or ""))

    def _refresh_categories(self) -> None:
        data = self.finance_service.list_categories(self.user_id)
        self.categories_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.categories_table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.categories_table.setItem(i, 1, QTableWidgetItem(row["name"]))
            self.categories_table.setItem(i, 2, QTableWidgetItem(row["type"]))

    def _refresh_dashboard(self) -> None:
        totals = self.finance_service.dashboard_totals_for_period(self.user_id, self.selected_year, self.selected_month)
        budget_overview = self.finance_service.monthly_budget_overview(self.user_id, self.selected_year, self.selected_month)
        budget_rows = self.finance_service.category_budget_status(self.user_id, self.selected_year, self.selected_month)
        inv = self.finance_service.investments_summary(self.user_id)
        self.total_income_lbl.setText(f"{totals['income']:.2f} PLN")
        self.total_expense_lbl.setText(f"{totals['expense']:.2f} PLN")
        total_balance = totals["balance"] + inv["total_profit_loss"]
        self.balance_lbl.setText(f"{total_balance:.2f} PLN")
        self.planned_budget_lbl.setText(f"{budget_overview['planned_budget']:.2f} PLN")
        self.unallocated_budget_lbl.setText(f"{budget_overview['unallocated_budget']:.2f} PLN")
        self.spent_percent_lbl.setText(f"{budget_overview['spent_percent_of_income']:.2f}%")
        self._fill_category_budget_table(budget_rows)
        alerts = self.finance_service.generate_monthly_alerts(self.user_id, self.selected_year, self.selected_month)
        if alerts:
            self.alerts_box.setPlainText("\n".join(f"- {a}" for a in alerts))
        else:
            self.alerts_box.setPlainText("Brak alertów dla wybranego miesiąca.")
        report = self.finance_service.build_monthly_report(self.user_id, self.selected_year, self.selected_month)
        self.monthly_report_box.setPlainText(self._format_monthly_report(report))
        self._plot_dashboard()

    def _fill_category_budget_table(self, rows: list[dict]) -> None:
        self.category_budget_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.category_budget_table.setItem(i, 0, QTableWidgetItem(row["category_name"]))
            self.category_budget_table.setItem(i, 1, QTableWidgetItem(f"{float(row['limit']):.2f}"))
            self.category_budget_table.setItem(i, 2, QTableWidgetItem(f"{float(row['spent']):.2f}"))
            self.category_budget_table.setItem(i, 3, QTableWidgetItem(f"{float(row['usage_percent']):.2f}%"))
            self.category_budget_table.setItem(i, 4, QTableWidgetItem(row["status"]))

    def _refresh_investments(self) -> None:
        summary = self.finance_service.investments_summary(self.user_id)
        self.inv_total_invested_lbl.setText(f"{summary['total_invested']:.2f} PLN")
        self.inv_total_current_lbl.setText(f"{summary['total_current']:.2f} PLN")
        self.inv_total_profit_lbl.setText(f"{summary['total_profit_loss']:.2f} PLN")

        data = self.finance_service.list_investments(self.user_id)
        self.investments_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.investments_table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.investments_table.setItem(i, 1, QTableWidgetItem(row["name"]))
            self.investments_table.setItem(i, 2, QTableWidgetItem(row["investment_type"]))
            self.investments_table.setItem(i, 3, QTableWidgetItem(row["purchase_date"]))
            self.investments_table.setItem(i, 4, QTableWidgetItem(f"{float(row['invested_amount']):.2f}"))
            self.investments_table.setItem(i, 5, QTableWidgetItem(f"{float(row['current_value']):.2f}"))
            self.investments_table.setItem(i, 6, QTableWidgetItem(f"{float(row['profit_loss']):.2f}"))
            self.investments_table.setItem(i, 7, QTableWidgetItem(f"{float(row['roi_percent']):.2f}%"))
            self.investments_table.setItem(i, 8, QTableWidgetItem(row["notes"] or ""))

    def _plot_dashboard(self) -> None:
        totals = self.finance_service.dashboard_totals_for_period(self.user_id, self.selected_year, self.selected_month)
        by_cat = self.finance_service.expenses_by_category_for_period(self.user_id, self.selected_year, self.selected_month)
        self.figure.clear()
        ax1 = self.figure.add_subplot(121)
        ax2 = self.figure.add_subplot(122)
        ax1.bar(["Przychody", "Wydatki"], [totals["income"], totals["expense"]], color=["#4CAF50", "#FF7043"])
        ax1.set_title("Przychody vs wydatki")
        if by_cat:
            labels = [x["category"] for x in by_cat]
            values = [float(x["total"]) for x in by_cat]
            ax2.pie(values, labels=labels, autopct="%1.0f%%")
            ax2.set_title("Wydatki wg kategorii")
        else:
            ax2.text(0.5, 0.5, "Brak danych", ha="center", va="center")
            ax2.set_title("Wydatki wg kategorii")
        self.canvas.draw()

    def _refresh_history(self) -> None:
        month = int(self.history_month.currentText()) if self.history_month.currentIndex() > 0 else None
        year = int(self.history_year.currentText()) if self.history_year.currentIndex() > 0 else None
        data = self.finance_service.list_history_filtered(
            self.user_id,
            txn_type=self.history_type.currentData(),
            date_from=self.history_from.text().strip(),
            date_to=self.history_to.text().strip(),
            year=year,
            month=month,
            category_id=self.history_category.currentData(),
            search_text=self.history_search.text().strip(),
        )
        self.history_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.history_table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.history_table.setItem(i, 1, QTableWidgetItem(row["type"]))
            self.history_table.setItem(i, 2, QTableWidgetItem(row["title"]))
            self.history_table.setItem(i, 3, QTableWidgetItem(f"{float(row['amount']):.2f}"))
            self.history_table.setItem(i, 4, QTableWidgetItem(row["txn_date"]))
            self.history_table.setItem(i, 5, QTableWidgetItem(row["category_name"] or ""))
            self.history_table.setItem(i, 6, QTableWidgetItem(row["note"] or ""))

    def _reset_history_filters(self) -> None:
        self.history_type.setCurrentIndex(0)
        self.history_from.clear()
        self.history_to.clear()
        self.history_month.setCurrentIndex(self.selected_month)
        year_idx = self.history_year.findText(str(self.selected_year))
        if year_idx >= 0:
            self.history_year.setCurrentIndex(year_idx)
        self.history_category.setCurrentIndex(0)
        self.history_search.clear()
        self._refresh_history()

    def _reset_transaction_filters(self, table: str) -> None:
        if table == "incomes":
            self.incomes_filter_from.clear()
            self.incomes_filter_to.clear()
            self.incomes_filter_search.clear()
            self.incomes_filter_category.setCurrentIndex(0)
        else:
            self.expenses_filter_from.clear()
            self.expenses_filter_to.clear()
            self.expenses_filter_search.clear()
            self.expenses_filter_category.setCurrentIndex(0)
        self._refresh_transactions(table)

    def _on_period_change(self) -> None:
        self.selected_month = int(self.month_selector.currentText())
        self.selected_year = int(self.year_selector.currentText())
        self.history_month.setCurrentIndex(self.selected_month)
        yidx = self.history_year.findText(str(self.selected_year))
        if yidx >= 0:
            self.history_year.setCurrentIndex(yidx)
        self._refresh_transactions("incomes")
        self._refresh_transactions("expenses")
        self._refresh_history()
        self._refresh_dashboard()

    def _format_monthly_report(self, report: dict) -> str:
        month_year = f"{report['year']}-{report['month']:02d}"
        top_lines = [f"- {x['category']}: {float(x['total']):.2f} PLN" for x in report["top_categories"]]
        top_text = "\n".join(top_lines) if top_lines else "- Brak danych"
        alerts_text = "\n".join(f"- {a}" for a in report["alerts"]) if report["alerts"] else "- Brak alertów"
        budget_text = "tak" if report["budget_exceeded"] else "nie"
        return (
            f"Raport za: {month_year}\n\n"
            f"Suma przychodów: {report['totals']['income']:.2f} PLN\n"
            f"Suma wydatków: {report['totals']['expense']:.2f} PLN\n"
            f"Saldo końcowe: {report['totals']['balance']:.2f} PLN\n"
            f"Liczba transakcji: {report['transaction_count']}\n"
            f"Budżet zaplanowany: {report['budget']:.2f} PLN\n"
            f"Pozostało do zaplanowania: {report['unallocated_budget']:.2f} PLN\n"
            f"Wydano % przychodu: {report['spent_percent_of_income']:.2f}%\n"
            f"Przekroczono budżet: {budget_text}\n\n"
            f"Top kategorie wydatków:\n{top_text}\n\n"
            f"Aktywne alerty:\n{alerts_text}\n\n"
            f"Podsumowanie: {report['summary_text']}"
        )

    def _save_profile(self) -> None:
        try:
            self.auth_service.update_profile(
                self.user_id,
                self.p_first_name.text(),
                self.p_last_name.text(),
                parse_amount(self.p_income.text()),
                parse_amount(self.p_rent.text()),
                parse_amount(self.p_goal.text()),
                self.p_password.text(),
            )
            QMessageBox.information(self, "Sukces", "Profil zaktualizowany.")
            self._refresh_profile()
        except Exception as exc:
            QMessageBox.warning(self, "Błąd", str(exc))

    def _active_table(self, table: str) -> QTableWidget:
        return self.incomes_table if table == "incomes" else self.expenses_table

    def _selected_id(self, table_widget: QTableWidget) -> int | None:
        row = table_widget.currentRow()
        if row < 0:
            return None
        item = table_widget.item(row, 0)
        if not item:
            return None
        return int(item.text())

    def _add_transaction(self, table: str) -> None:
        cat_type = "income" if table == "incomes" else "expense"
        categories = self.finance_service.list_categories(self.user_id, cat_type)
        dialog = TransactionDialog(categories, "Nowa transakcja", parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.result_data:
            try:
                self.finance_service.add_transaction(table, self.user_id, **dialog.result_data)
                self._refresh_transactions(table)
                self._refresh_dashboard()
            except Exception as exc:
                QMessageBox.warning(self, "Błąd", str(exc))

    def _edit_transaction(self, table: str) -> None:
        tbl = self._active_table(table)
        txn_id = self._selected_id(tbl)
        if not txn_id:
            QMessageBox.information(self, "Informacja", "Wybierz rekord do edycji.")
            return
        row = tbl.currentRow()
        current = {
            "title": tbl.item(row, 1).text(),
            "amount": float(tbl.item(row, 2).text()),
            "txn_date": tbl.item(row, 3).text(),
            "note": tbl.item(row, 5).text(),
            "category_id": None,
        }
        cat_type = "income" if table == "incomes" else "expense"
        categories = self.finance_service.list_categories(self.user_id, cat_type)
        dialog = TransactionDialog(categories, "Edycja transakcji", current, self)
        if dialog.exec() == QDialog.Accepted and dialog.result_data:
            try:
                self.finance_service.update_transaction(table, txn_id, self.user_id, **dialog.result_data)
                self._refresh_transactions(table)
                self._refresh_dashboard()
            except Exception as exc:
                QMessageBox.warning(self, "Błąd", str(exc))

    def _delete_transaction(self, table: str) -> None:
        tbl = self._active_table(table)
        txn_id = self._selected_id(tbl)
        if not txn_id:
            QMessageBox.information(self, "Informacja", "Wybierz rekord do usunięcia.")
            return
        self.finance_service.delete_transaction(table, txn_id, self.user_id)
        self._refresh_transactions(table)
        self._refresh_dashboard()

    def _add_category(self) -> None:
        try:
            if not self.category_name.text().strip():
                raise ValueError("Nazwa kategorii jest wymagana.")
            self.finance_service.add_category(self.user_id, self.category_name.text(), self.category_type.currentText())
            self.category_name.clear()
            self._refresh_categories()
        except Exception as exc:
            QMessageBox.warning(self, "Błąd", str(exc))

    def _delete_category(self) -> None:
        idx = self._selected_id(self.categories_table)
        if not idx:
            QMessageBox.information(self, "Informacja", "Wybierz kategorię.")
            return
        self.finance_service.delete_category(idx, self.user_id)
        self._refresh_categories()

    def _add_investment(self) -> None:
        dialog = InvestmentDialog(self.finance_service.INVESTMENT_TYPES, "Nowa inwestycja", parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.result_data:
            try:
                self.finance_service.add_investment(self.user_id, **dialog.result_data)
                self._refresh_investments()
                self._refresh_dashboard()
            except Exception as exc:
                QMessageBox.warning(self, "Błąd", str(exc))

    def _edit_investment(self) -> None:
        investment_id = self._selected_id(self.investments_table)
        if not investment_id:
            QMessageBox.information(self, "Informacja", "Wybierz inwestycję do edycji.")
            return
        row = self.investments_table.currentRow()
        current = {
            "name": self.investments_table.item(row, 1).text(),
            "investment_type": self.investments_table.item(row, 2).text(),
            "purchase_date": self.investments_table.item(row, 3).text(),
            "invested_amount": float(self.investments_table.item(row, 4).text()),
            "current_value": float(self.investments_table.item(row, 5).text()),
            "notes": self.investments_table.item(row, 8).text(),
        }
        dialog = InvestmentDialog(self.finance_service.INVESTMENT_TYPES, "Edycja inwestycji", current, self)
        if dialog.exec() == QDialog.Accepted and dialog.result_data:
            try:
                self.finance_service.update_investment(investment_id, self.user_id, **dialog.result_data)
                self._refresh_investments()
                self._refresh_dashboard()
            except Exception as exc:
                QMessageBox.warning(self, "Błąd", str(exc))

    def _delete_investment(self) -> None:
        investment_id = self._selected_id(self.investments_table)
        if not investment_id:
            QMessageBox.information(self, "Informacja", "Wybierz inwestycję do usunięcia.")
            return
        self.finance_service.delete_investment(investment_id, self.user_id)
        self._refresh_investments()
        self._refresh_dashboard()

    def _save_budget(self) -> None:
        try:
            month_key = f"{self.selected_year:04d}-{self.selected_month:02d}"
            category_id = self.budget_category_selector.currentData()
            if category_id is None:
                raise ValueError("Wybierz kategorię budżetu.")
            self.finance_service.save_category_budget(
                self.user_id, month_key, int(category_id), parse_amount(self.budget_input.text())
            )
            self._refresh_dashboard()
            QMessageBox.information(self, "Sukces", "Limit kategorii zapisany.")
        except Exception as exc:
            QMessageBox.warning(self, "Błąd", str(exc))

    def _export_csv(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "Zapisz CSV", "finanse.csv", "CSV (*.csv)")
        if not file_path:
            return
        incomes = self.finance_service.list_transactions("incomes", self.user_id)
        expenses = self.finance_service.list_transactions("expenses", self.user_id)
        ExportService.export_csv(Path(file_path), incomes, expenses)
        QMessageBox.information(self, "Eksport", "Plik CSV został zapisany.")

    def _export_pdf(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "Zapisz PDF", "raport.pdf", "PDF (*.pdf)")
        if not file_path:
            return
        totals = self.finance_service.dashboard_totals(self.user_id)
        by_category = self.finance_service.expenses_by_category(self.user_id)
        ExportService.export_pdf(Path(file_path), totals, by_category)
        QMessageBox.information(self, "Eksport", "Plik PDF został zapisany.")

    def _run_ai(self) -> None:
        user = self.auth_service.get_user(self.user_id)
        totals = self.finance_service.dashboard_totals(self.user_id)
        by_category = self.finance_service.expenses_by_category(self.user_id)
        ratio = self.finance_service.monthly_ratio(self.user_id)
        prompt = self.gemini_service.build_prompt(user, totals, by_category, ratio)
        answer = self.gemini_service.analyze(prompt)
        self.ai_text.setPlainText(answer)
        self.ai_status.setText("AI: aktywne" if self.gemini_service.available() else "AI: brak klucza API")

    def _import_csv(self, table: str) -> None:
        try:
            title = "Wybierz plik CSV"
            file_path, _ = QFileDialog.getOpenFileName(self, title, "", "CSV (*.csv)")
            if not file_path:
                return
            result = self.finance_service.import_transactions_from_csv(self.user_id, table, file_path)
            imported = result["imported"]
            errors = result["errors"]
            self.refresh_all()

            if errors:
                preview = "\n".join(errors[:10])
                if len(errors) > 10:
                    preview += f"\n... i {len(errors) - 10} kolejnych błędów."
                QMessageBox.warning(
                    self,
                    "Import zakończony z błędami",
                    f"Zaimportowano rekordów: {imported}\nBłędnych wierszy: {len(errors)}\n\n{preview}",
                )
            else:
                QMessageBox.information(self, "Import", f"Zaimportowano rekordów: {imported}")
        except Exception as exc:
            QMessageBox.warning(self, "Błąd", str(exc))
