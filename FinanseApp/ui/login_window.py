from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from services.auth_service import AuthService
from utils.validators import parse_amount


class LoginWindow(QWidget):
    logged_in = Signal(int)

    def __init__(self, auth_service: AuthService) -> None:
        super().__init__()
        self.auth_service = auth_service
        self.setWindowTitle("FinanseApp - Logowanie")
        self.resize(420, 340)
        self._build_ui()
        self._sync_mode()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        root.addWidget(self.info_label)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self.login_page = QWidget()
        login_form = QFormLayout(self.login_page)
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        login_form.addRow("Hasło:", self.login_password)
        self.login_btn = QPushButton("Zaloguj")
        self.login_btn.clicked.connect(self._on_login)
        login_form.addRow(self.login_btn)
        self.stack.addWidget(self.login_page)

        self.register_page = QWidget()
        reg_form = QFormLayout(self.register_page)
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.monthly_income = QLineEdit("0")
        self.rent = QLineEdit("0")
        self.savings_goal = QLineEdit("0")
        reg_form.addRow("Imię:", self.first_name)
        reg_form.addRow("Nazwisko:", self.last_name)
        reg_form.addRow("Hasło:", self.password)
        reg_form.addRow("Miesięczny dochód:", self.monthly_income)
        reg_form.addRow("Czynsz:", self.rent)
        reg_form.addRow("Cel oszczędności:", self.savings_goal)
        row = QHBoxLayout()
        self.register_btn = QPushButton("Zarejestruj")
        self.register_btn.clicked.connect(self._on_register)
        row.addWidget(self.register_btn)
        reg_form.addRow(row)
        self.stack.addWidget(self.register_page)

    def _sync_mode(self) -> None:
        if self.auth_service.has_user():
            self.info_label.setText("Witaj ponownie. Podaj hasło, aby przejść dalej.")
            self.stack.setCurrentWidget(self.login_page)
        else:
            self.info_label.setText("Pierwsze uruchomienie. Utwórz konto użytkownika.")
            self.stack.setCurrentWidget(self.register_page)

    def _on_register(self) -> None:
        try:
            if not self.first_name.text().strip() or not self.last_name.text().strip():
                raise ValueError("Imię i nazwisko są wymagane.")
            user_id = self.auth_service.register_first_user(
                self.first_name.text(),
                self.last_name.text(),
                self.password.text(),
                parse_amount(self.monthly_income.text()),
                parse_amount(self.rent.text()),
                parse_amount(self.savings_goal.text()),
            )
            QMessageBox.information(self, "Sukces", "Konto utworzone. Zalogowano.")
            self.logged_in.emit(user_id)
        except Exception as exc:
            QMessageBox.warning(self, "Błąd rejestracji", str(exc))

    def _on_login(self) -> None:
        try:
            user_id = self.auth_service.login(self.login_password.text())
            self.logged_in.emit(user_id)
        except Exception as exc:
            QMessageBox.warning(self, "Błąd logowania", str(exc))
