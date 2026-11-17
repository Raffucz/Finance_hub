from decimal import Decimal
from hashlib import sha256
import pandas as pd


COLUMN_ALIASES = {
    "date": ["date", "data", "dt_transacao"],
    "amount": ["amount", "valor", "value"],
    "description": ["description", "descrição", "descricao", "title", "historico", "histórico"],
    "id": ["transaction_id", "identificador", "id"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower_cols = {col.strip().lower(): col for col in df.columns}
    rename_map = {}

    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                rename_map[lower_cols[alias]] = target
                break

    df = df.rename(columns=rename_map)
    missing = {"date", "amount", "description"} - set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes no CSV: {missing}. Encontradas: {list(df.columns)}")
    return df


def _parse_decimal(val) -> Decimal:
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    cleaned = str(val).strip().replace("R$", "").strip()
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return Decimal(cleaned)


def parse_csv(file_path: str) -> list[dict]:
    # Detecta separador automaticamente (, ou ;)
    df = pd.read_csv(file_path, sep=None, engine="python", encoding="utf-8-sig")
    df = _normalize_columns(df)

    df["parsed_date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["parsed_date", "amount", "description"])

    transactions: list[dict] = []
    seen_hashes: set[str] = set()

    for idx, row in df.iterrows():
        amount = _parse_decimal(row["amount"])
        description = str(row["description"]).strip()
        tx_date = str(row["parsed_date"])

        source_hash = sha256(f"{tx_date}_{amount}_{description.lower()}".encode("utf-8")).hexdigest()
        if source_hash in seen_hashes:
            continue
        seen_hashes.add(source_hash)

        tx_id = str(row["id"]) if "id" in df.columns and pd.notna(row["id"]) else source_hash[:16]

        transactions.append({
            "id": tx_id,
            "source_hash": source_hash,
            "date": tx_date,
            "amount": amount,
            "description": description,
        })

    return transactions