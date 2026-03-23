import sys

from PySide6.QtWidgets import QApplication

from database.db_manager import DatabaseManager
from services.auth_service import AuthService
from services.finance_service import FinanceService
from services.gemini_service import GeminiService
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("FinanseApp")

    db = DatabaseManager()
    auth_service = AuthService(db)
    finance_service = FinanceService(db)
    gemini_service = GeminiService()

    login_window = LoginWindow(auth_service)
    main_window = MainWindow(auth_service, finance_service, gemini_service)

    def on_logged_in(user_id: int) -> None:
        main_window.set_user(user_id)
        main_window.refresh_all()
        main_window.show()
        login_window.close()

    login_window.logged_in.connect(on_logged_in)
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
