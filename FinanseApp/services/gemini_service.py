import json
from datetime import datetime
from urllib import error, request

from config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiService:
    def __init__(self) -> None:
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL

    def available(self) -> bool:
        return bool(self.api_key)

    def build_prompt(self, user_data: dict, totals: dict, by_category: list[dict], ratio: dict) -> str:
        category_text = "\n".join(f"- {row['category']}: {float(row['total']):.2f} PLN" for row in by_category) or "- Brak danych"
        return (
            "Jestes doradca finansow domowych. Odpowiedz po polsku, zwiezle i praktycznie.\n"
            "Nie wykonuj zadnych operacji finansowych. Tylko analiza i wskazowki.\n\n"
            f"Data: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"Uzytkownik: {user_data['first_name']} {user_data['last_name']}\n"
            f"Miesieczny dochod z profilu: {float(user_data['monthly_income']):.2f}\n"
            f"Czynsz: {float(user_data['rent']):.2f}\n"
            f"Cel oszczednosci: {float(user_data['savings_goal']):.2f}\n\n"
            f"Suma przychodow: {totals['income']:.2f}\n"
            f"Suma wydatkow: {totals['expense']:.2f}\n"
            f"Saldo: {totals['balance']:.2f}\n"
            f"Przychody miesiac: {ratio['month_income']:.2f}\n"
            f"Wydatki miesiac: {ratio['month_expense']:.2f}\n"
            f"Budzet miesiac: {ratio['budget']:.2f}\n\n"
            "Wydatki wg kategorii:\n"
            f"{category_text}\n\n"
            "Podaj: 1) krotkie podsumowanie miesiaca, 2) ryzyko przekroczenia budzetu, "
            "3) 3 mozliwe oszczednosci, 4) jedna konkretna rekomendacje."
        )

    def analyze(self, prompt: str) -> str:
        if not self.available():
            return "Brak klucza GEMINI_API_KEY. Funkcja AI jest wyłączona."

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                    ]
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            candidates = body.get("candidates", [])
            if not candidates:
                return "AI nie zwrocilo odpowiedzi."
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return "AI nie zwrocilo tresci."
            text = parts[0].get("text", "").strip()
            return text or "AI zwrocilo pusty tekst."
        except error.HTTPError as exc:
            return f"Blad Gemini API: {exc.code}"
        except Exception:
            return "Nie udalo sie pobrac odpowiedzi AI."
