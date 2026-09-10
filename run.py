#!/usr/bin/env python3
"""Baixa os dados oficiais FEVEROUS ausentes e executa o exportador de CSV.

Uso:
    python run.py

Não depende de wget, curl, shell script ou utilitários específicos do sistema
operacional; portanto funciona da mesma forma no Windows, Linux e macOS.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
EXPORTER = ROOT / "export_graph_ready_csv.py"

DATA_URLS = {
    "train.jsonl": "https://fever.ai/download/feverous/feverous_train_challenges.jsonl",
    "dev.jsonl": "https://fever.ai/download/feverous/feverous_dev_challenges.jsonl",
    "test_unlabeled.jsonl": "https://fever.ai/download/feverous/feverous_test_unlabeled.jsonl",
}
DATABASE_NAME = "feverous_wikiv1.db"
DATABASE_URL = "https://fever.ai/download/feverous/feverous-wiki-pages-db.zip"


def download(url: str, destination: Path) -> None:
    """Baixa ``url`` de forma atômica, evitando arquivos finais incompletos."""
    temporary = destination.with_name(destination.name + ".part")
    print(f"Baixando {destination.name}...")

    def report(block_number: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            percent = min(100, block_number * block_size * 100 // total_size)
            print(f"\r  {percent:3d}%", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, temporary, reporthook=report)
        print()
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def archive_contains_database(archive: Path) -> bool:
    """Verifica se o ZIP pode ser lido e contém o banco esperado."""
    try:
        with zipfile.ZipFile(archive) as zip_file:
            return any(Path(item.filename).name == DATABASE_NAME for item in zip_file.infolist())
    except zipfile.BadZipFile:
        return False


def ensure_dataset() -> None:
    """Garante que os JSONL e o banco SQLite exigidos pelo exportador existam."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in DATA_URLS.items():
        destination = DATA_DIR / filename
        if destination.is_file() and destination.stat().st_size > 0:
            print(f"Encontrado: {destination.name}")
        else:
            download(url, destination)

    database = DATA_DIR / DATABASE_NAME
    if database.is_file() and database.stat().st_size > 0:
        print(f"Encontrado: {database.name}")
        return

    archive = DATA_DIR / "feverous-wiki-pages-db.zip"
    if archive.is_file() and archive.stat().st_size > 0 and archive_contains_database(archive):
        print(f"Encontrado: {archive.name}")
    else:
        if archive.exists():
            print(f"Arquivo inválido removido: {archive.name}")
            archive.unlink()
        download(DATABASE_URL, archive)
    print(f"Extraindo {DATABASE_NAME}...")
    try:
        with zipfile.ZipFile(archive) as zip_file:
            member = next(
                (item for item in zip_file.infolist() if Path(item.filename).name == DATABASE_NAME),
                None,
            )
            if member is None:
                raise RuntimeError(f"{DATABASE_NAME} não foi encontrado no arquivo baixado.")
            available_space = shutil.disk_usage(DATA_DIR).free
            if available_space < member.file_size:
                required_gib = member.file_size / 1024**3
                available_gib = available_space / 1024**3
                raise RuntimeError(
                    f"Espaço insuficiente para extrair o banco: são necessários "
                    f"{required_gib:.1f} GiB livres e há somente {available_gib:.1f} GiB."
                )
            with zip_file.open(member) as source, database.open("wb") as target:
                shutil.copyfileobj(source, target)
    except Exception:
        database.unlink(missing_ok=True)
        raise
    archive.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "exporter_args",
        nargs=argparse.REMAINDER,
        help="argumentos opcionais repassados a export_graph_ready_csv.py; use -- antes deles",
    )
    args = parser.parse_args()

    if not EXPORTER.is_file():
        raise FileNotFoundError(f"Exportador não encontrado: {EXPORTER}")

    ensure_dataset()
    command = [sys.executable, str(EXPORTER), *args.exporter_args]
    print("Executando exportador...")
    subprocess.run(command, check=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Erro: {error}", file=sys.stderr)
        raise SystemExit(1)
