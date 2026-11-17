from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.finance.models.transaction import Transaction


class FinanceAICopilot:
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "nous-hermes2:latest"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def build_financial_context(self, db: AsyncSession, months: int = 3) -> str:
        cutoff_date = date.today() - timedelta(days=30 * months)

        # 1. Totais de entradas e saídas no período
        totals_query = select(
            func.coalesce(func.sum(Transaction.amount).filter(Transaction.amount > 0), 0).label("total_in"),
            func.coalesce(func.sum(Transaction.amount).filter(Transaction.amount < 0), 0).label("total_out"),
            func.count(Transaction.id).label("tx_count"),
        ).where(Transaction.date >= cutoff_date)

        totals = (await db.execute(totals_query)).one()
        total_in = Decimal(totals.total_in)
        total_out = Decimal(totals.total_out)
        net_balance = total_in + total_out

        # 2. Gastos agrupados por categoria (apenas saídas)
        cat_query = (
            select(
                Transaction.category,
                func.sum(Transaction.amount).label("cat_total"),
                func.count(Transaction.id).label("cat_count"),
            )
            .where(Transaction.date >= cutoff_date, Transaction.amount < 0)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).asc())
        )
        categories = (await db.execute(cat_query)).all()

        # 3. Top 15 maiores despesas individuais
        top_expenses_query = (
            select(Transaction)
            .where(Transaction.date >= cutoff_date, Transaction.amount < 0)
            .order_by(Transaction.amount.asc())
            .limit(15)
        )
        top_expenses = (await db.execute(top_expenses_query)).scalars().all()

        # 4. Top 5 maiores entradas individuais
        top_income_query = (
            select(Transaction)
            .where(Transaction.date >= cutoff_date, Transaction.amount > 0)
            .order_by(Transaction.amount.desc())
            .limit(5)
        )
        top_incomes = (await db.execute(top_income_query)).scalars().all()

        lines = [
            f"=== RESUMO FINANCEIRO (Últimos {months} meses | {totals.tx_count} transações) ===",
            f"- Total de Entradas: R$ {total_in:,.2f}",
            f"- Total de Saídas: R$ {abs(total_out):,.2f}",
            f"- Saldo Líquido do Período: R$ {net_balance:,.2f}",
            "",
            "=== GASTOS POR CATEGORIA ===",
        ]
        for cat in categories:
            lines.append(f"- {cat.category}: R$ {abs(Decimal(cat.cat_total)):,.2f} ({cat.cat_count} transações)")

        lines.extend(["", "=== TOP 15 MAIORES DESPESAS ==="])
        for tx in top_expenses:
            lines.append(f"- [{tx.date.isoformat()}] R$ {abs(tx.amount):,.2f} | {tx.category} | {tx.description}")

        lines.extend(["", "=== PRINCIPAIS ENTRADAS ==="])
        for tx in top_incomes:
            lines.append(f"- [{tx.date.isoformat()}] R$ {tx.amount:,.2f} | {tx.category} | {tx.description}")

        return "\n".join(lines)

    async def _generate(self, prompt: str, system_prompt: str, model: str | None = None) -> str:
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            },
        }
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                return response.json().get("response", "").strip()
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Não foi possível conectar ao Ollama em http://localhost:11434. Verifique se ele está rodando.",
            )
        except httpx.ReadTimeout:
            raise HTTPException(
                status_code=504,
                detail=f"O modelo '{target_model}' demorou mais de 5 minutos para responder.",
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Erro no Ollama ({exc.response.status_code}): {exc.response.text}",
            )

    async def answer_question(
        self, db: AsyncSession, question: str, months: int = 3, model: str | None = None
    ) -> dict:
        context = await self.build_financial_context(db, months=months)
        system_prompt = (
            "Você é um analista financeiro pessoal direto e preciso. "
            "Responda sempre em Português (Brasil) usando apenas os dados fornecidos no contexto abaixo. "
            "Não invente valores ou transações que não estejam nos dados. Cite os números exatos em R$."
        )
        prompt = f"{context}\n\nPergunta do usuário: {question}"
        answer = await self._generate(prompt=prompt, system_prompt=system_prompt, model=model)
        return {"question": question, "model": model or self.default_model, "answer": answer}

    async def generate_insights(
        self, db: AsyncSession, months: int = 3, model: str | None = None
    ) -> dict:
        context = await self.build_financial_context(db, months=months)
        system_prompt = (
            "Você é um consultor financeiro objetivo e analítico. "
            "Analise o extrato resumido em Português (Brasil) e produza um relatório curto e acionável."
        )
        prompt = (
            f"{context}\n\n"
            "Com base nesses dados reais, gere um diagnóstico contendo:\n"
            "1. **Saúde Financeira Geral**: análise rápida entre entradas, saídas e saldo líquido.\n"
            "2. **Principais Vilões e Padrões**: quais categorias mais pesam e se há gastos recorrentes/assinaturas relevantes.\n"
            "3. **3 Ações Práticas**: recomendações diretas para economizar no próximo mês citando estabelecimentos/categorias reais do extrato."
        )
        insights = await self._generate(prompt=prompt, system_prompt=system_prompt, model=model)
        return {"months_analyzed": months, "model": model or self.default_model, "insights": insights}