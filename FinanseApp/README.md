# FinanseApp

Desktopowa aplikacja do zarządzania finansami domowymi (jeden użytkownik), oparta o Python + PySide6 + SQLite.

## Funkcje

- Rejestracja pierwszego użytkownika i logowanie hasłem.
- Profil użytkownika (imię, nazwisko, hasło, dochód, czynsz, cel oszczędności).
- Zarządzanie przychodami i wydatkami (dodawanie, edycja, usuwanie).
- Kategorie transakcji.
- Dashboard: suma przychodów, suma wydatków, saldo.
- Wykresy: przychody vs wydatki oraz wydatki według kategorii.
- Budżet miesięczny i podstawowe alerty.
- Eksport CSV i PDF.
- Opcjonalna analiza AI (Google Gemini API).

## Uruchomienie

1. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```
2. Skopiuj `.env.example` do `.env` i wpisz `GEMINI_API_KEY` (opcjonalnie).
3. Uruchom:
   ```bash
   python main.py
   ```

## Budowa .exe

```bash
pyinstaller --noconfirm --windowed --name FinanseApp main.py
```

Plik gotowy będzie w `dist/FinanseApp/`.
