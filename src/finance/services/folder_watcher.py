import asyncio
import logging
from pathlib import Path
import shutil
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from src.finance.core.database import AsyncSessionLocal
from src.finance.services.categorize import CategorizationService
from src.finance.services.transaction_service import TransactionService

logger = logging.getLogger("uvicorn")

INBOX_DIR = Path("inbox")
PROCESSED_DIR = INBOX_DIR / "processed"
SUPPORTED_EXTENSIONS = {".csv", ".ofx"}


async def process_file(file_path: Path) -> None:
    if not file_path.exists() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return

    file_type = file_path.suffix.lower().lstrip(".")
    try:
        categorizer = CategorizationService()
        raw_transactions = categorizer.categorize_transactions(str(file_path), file_type=file_type)

        async with AsyncSessionLocal() as db:
            tx_service = TransactionService()
            result = await tx_service.save_transactions(db, raw_transactions)

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = PROCESSED_DIR / file_path.name
        if dest_path.exists():
            dest_path.unlink()
        shutil.move(str(file_path), str(dest_path))

        logger.info(
            f"[Hot-Folder] Arquivo '{file_path.name}' importado com sucesso: "
            f"{result['inserted']} inseridas, {result['duplicates_skipped']} duplicadas ignoradas."
        )
    except Exception as exc:
        logger.error(f"[Hot-Folder] Erro ao processar '{file_path.name}': {exc}")


class InboxEventHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def on_created(self, event) -> None:
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if PROCESSED_DIR in file_path.parents or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        # Aguarda 1 segundo para o Windows finalizar a escrita/cópia do arquivo
        time.sleep(1)
        asyncio.run_coroutine_threadsafe(process_file(file_path), self.loop)


def start_watcher(loop: asyncio.AbstractEventLoop) -> Observer:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Processa arquivos que já estavam na inbox antes do servidor subir
    for existing_file in INBOX_DIR.iterdir():
        if existing_file.is_file() and existing_file.suffix.lower() in SUPPORTED_EXTENSIONS:
            asyncio.run_coroutine_threadsafe(process_file(existing_file), loop)

    observer = Observer()
    observer.schedule(InboxEventHandler(loop), str(INBOX_DIR), recursive=False)
    observer.start()
    logger.info(f"[Hot-Folder] Monitorando a pasta '{INBOX_DIR.resolve()}'...")
    return observer


def stop_watcher(observer: Observer) -> None:
    observer.stop()
    observer.join()