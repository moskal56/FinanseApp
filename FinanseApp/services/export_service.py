import csv
from pathlib import Path

from fpdf import FPDF


class ExportService:
    @staticmethod
    def export_csv(path: Path, incomes: list[dict], expenses: list[dict]) -> None:
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerow(["type", "title", "amount", "date", "category", "note"])
            for row in incomes:
                writer.writerow(["income", row["title"], row["amount"], row["txn_date"], row["category_name"] or "", row["note"] or ""])
            for row in expenses:
                writer.writerow(["expense", row["title"], row["amount"], row["txn_date"], row["category_name"] or "", row["note"] or ""])

    @staticmethod
    def export_pdf(path: Path, totals: dict[str, float], expenses_by_category: list[dict]) -> None:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)
        pdf.cell(0, 10, txt="Raport FinanseApp", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 8, txt=f"Suma przychodow: {totals['income']:.2f} PLN", ln=True)
        pdf.cell(0, 8, txt=f"Suma wydatkow: {totals['expense']:.2f} PLN", ln=True)
        pdf.cell(0, 8, txt=f"Saldo: {totals['balance']:.2f} PLN", ln=True)
        pdf.ln(4)
        pdf.cell(0, 8, txt="Wydatki wg kategorii:", ln=True)
        for row in expenses_by_category:
            pdf.cell(0, 8, txt=f"- {row['category']}: {float(row['total']):.2f} PLN", ln=True)
        pdf.output(str(path))
