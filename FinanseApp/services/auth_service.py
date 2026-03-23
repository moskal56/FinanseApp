from database.db_manager import DatabaseManager
from utils.security import hash_password, verify_password


class AuthService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def has_user(self) -> bool:
        row = self.db.fetchone("SELECT id FROM users LIMIT 1")
        return row is not None

    def register_first_user(
        self,
        first_name: str,
        last_name: str,
        password: str,
        monthly_income: float,
        rent: float,
        savings_goal: float,
    ) -> int:
        if self.has_user():
            raise ValueError("Użytkownik już istnieje.")
        if len(password) < 6:
            raise ValueError("Hasło musi mieć minimum 6 znaków.")

        user_id = self.db.execute(
            """
            INSERT INTO users(first_name, last_name, password_hash, monthly_income, rent, savings_goal)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (first_name.strip(), last_name.strip(), hash_password(password), monthly_income, rent, savings_goal),
        )
        self._seed_default_categories(user_id)
        return user_id

    def _seed_default_categories(self, user_id: int) -> None:
        income = ["Wynagrodzenie", "Premia", "Inne"]
        expense = ["Jedzenie", "Transport", "Mieszkanie", "Rozrywka", "Zdrowie", "Inne"]
        for name in income:
            self.db.execute(
                "INSERT OR IGNORE INTO categories(user_id, name, type) VALUES (?, ?, 'income')",
                (user_id, name),
            )
        for name in expense:
            self.db.execute(
                "INSERT OR IGNORE INTO categories(user_id, name, type) VALUES (?, ?, 'expense')",
                (user_id, name),
            )

    def login(self, password: str) -> int:
        user = self.db.fetchone("SELECT id, password_hash FROM users LIMIT 1")
        if not user:
            raise ValueError("Brak użytkownika. Zarejestruj konto.")
        if not verify_password(password, user["password_hash"]):
            raise ValueError("Nieprawidłowe hasło.")
        return int(user["id"])

    def get_user(self, user_id: int) -> dict:
        row = self.db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not row:
            raise ValueError("Nie znaleziono użytkownika.")
        return dict(row)

    def update_profile(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        monthly_income: float,
        rent: float,
        savings_goal: float,
        new_password: str = "",
    ) -> None:
        self.db.execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, monthly_income = ?, rent = ?, savings_goal = ?
            WHERE id = ?
            """,
            (first_name.strip(), last_name.strip(), monthly_income, rent, savings_goal, user_id),
        )
        if new_password.strip():
            if len(new_password) < 6:
                raise ValueError("Nowe hasło musi mieć minimum 6 znaków.")
            self.db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password.strip()), user_id),
            )
