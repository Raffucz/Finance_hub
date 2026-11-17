from datetime import date, timedelta
from rapidfuzz import fuzz
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.finance.models.transaction import Transaction


class TransactionService:
    async def save_transactions(self, db: AsyncSession, raw_transactions: list[dict]) -> dict:
        inserted_count = 0
        duplicates_skipped = 0
        seen_batch_hashes: set[str] = set()

        for raw_tx in raw_transactions:
            tx_hash = raw_tx["source_hash"]
            if tx_hash in seen_batch_hashes:
                duplicates_skipped += 1
                continue

            # 1. Deduplicação exata por hash SHA-256
            existing_tx = await db.scalar(
                select(Transaction).where(Transaction.source_hash == tx_hash)
            )
            if existing_tx:
                duplicates_skipped += 1
                continue

            # 2. Deduplicação fuzzy (±2 dias + mesmo valor + descrição > 85% similar)
            tx_date = date.fromisoformat(raw_tx["date"])
            date_start = tx_date - timedelta(days=2)
            date_end = tx_date + timedelta(days=2)

            candidates = (
                await db.execute(
                    select(Transaction).where(
                        and_(
                            Transaction.amount == raw_tx["amount"],
                            Transaction.date >= date_start,
                            Transaction.date <= date_end,
                        )
                    )
                )
            ).scalars().all()

            is_fuzzy_dup = any(
                fuzz.ratio(cand.description.lower(), raw_tx["description"].lower()) > 85
                for cand in candidates
            )
            if is_fuzzy_dup:
                duplicates_skipped += 1
                continue

            # 3. Persistência no PostgreSQL
            new_tx = Transaction(
                date=tx_date,
                amount=raw_tx["amount"],
                description=raw_tx["description"],
                category=raw_tx["category"],
                confidence=raw_tx["confidence"],
                source_hash=tx_hash,
            )
            db.add(new_tx)
            seen_batch_hashes.add(tx_hash)
            inserted_count += 1

        await db.commit()
        return {"inserted": inserted_count, "duplicates_skipped": duplicates_skipped}

    async def list_transactions(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        category: str | None = None,
    ) -> list[Transaction]:
        query = select(Transaction).order_by(Transaction.date.desc())
        if category:
            query = query.where(Transaction.category == category)
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())