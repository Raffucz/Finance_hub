import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
import os
from tempfile import NamedTemporaryFile
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.finance.core.database import Base, engine, get_db
from src.finance.models import transaction as _models  # noqa: F401
from src.finance.services.categorize import CategorizationService
from src.finance.services.folder_watcher import start_watcher, stop_watcher
from src.finance.services.transaction_service import TransactionService
from src.finance.services.ai_copilot import FinanceAICopilot


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    loop = asyncio.get_running_loop()
    observer = start_watcher(loop)
    yield
    stop_watcher(observer)


app = FastAPI(title="Finance Hub API", version="0.2.0", lifespan=lifespan)

class AIQuestionRequest(BaseModel):
    question: str
    months: int = 3
    model: str | None = None


class AIInsightsRequest(BaseModel):
    months: int = 3
    model: str | None = None


@app.post("/ai/ask", response_model=dict)
async def ask_financial_copilot(
    payload: AIQuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    copilot = FinanceAICopilot()
    return await copilot.answer_question(
        db, question=payload.question, months=payload.months, model=payload.model
    )


@app.post("/ai/insights", response_model=dict)
async def generate_financial_insights(
    payload: AIInsightsRequest,
    db: AsyncSession = Depends(get_db),
):
    copilot = FinanceAICopilot()
    return await copilot.generate_insights(db, months=payload.months, model=payload.model)