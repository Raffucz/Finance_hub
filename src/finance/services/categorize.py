from src.finance.ingestion.parse_csv import parse_csv
from src.finance.ingestion.parse_ofx import parse_ofx
from src.finance.ml.categorizer import Categorizer


class CategorizationService:
    def __init__(self):
        self.categorizer = Categorizer()

    def categorize_transactions(self, file_path: str, file_type: str = "csv") -> list[dict]:
        if file_type == "csv":
            transactions = parse_csv(file_path)
        elif file_type == "ofx":
            transactions = parse_ofx(file_path)
        else:
            raise ValueError(f"Tipo de arquivo não suportado: {file_type}")

        if not transactions:
            return []

        descriptions = [tx["description"] for tx in transactions]
        predictions = self.categorizer.categorize(descriptions)

        for tx, (category, confidence) in zip(transactions, predictions):
            tx["date"] = str(tx["date"])[:10]
            tx["category"] = category
            tx["confidence"] = round(confidence, 2)

        return transactions