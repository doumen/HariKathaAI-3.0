#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HariKathaAI – Gerenciador de Backups Robusto
Localização ideal: src/scripts/backup_harikatha.py
"""

import os
import sys
import gc
import time
import gzip
import shutil
import logging
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------
# CONFIGURAÇÃO DE CAMINHOS
# ----------------------------------------------------------------------
# Como este script está em src/scripts/, precisamos subir 3 níveis para chegar à raiz
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent.parent

DB_PATH = BASE_DIR / "database" / "harikatha.db"
BACKUP_ROOT = BASE_DIR / "backups"

# Sub‑diretórios de backup
LOCAL_DAILY   = BACKUP_ROOT / "daily"
LOCAL_MONTHLY = BACKUP_ROOT / "monthly"

# Política de retenção
KEEP_DAILY_DAYS   = 30   # dias de backups diários
KEEP_MONTHLY_COUNT = 12  # quantos backups mensais manter

# Remote rclone (deixe vazio para desativar a sincronização)
RCLONE_REMOTE = "gdrive:HariKathaAI/Backups"

# ----------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------
os.makedirs(BACKUP_ROOT, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BACKUP_ROOT / "backup.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("backup")

# ----------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ----------------------------------------------------------------------
def ensure_structure() -> None:
    """Cria diretórios de backup."""
    for p in (LOCAL_DAILY, LOCAL_MONTHLY):
        p.mkdir(parents=True, exist_ok=True)

def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def atomic_sqlite_backup() -> Path | None:
    if not DB_PATH.is_file():
        log.error("Banco de dados não encontrado em: %s", DB_PATH)
        log.error("Verifique se a variável BASE_DIR está apontando para a raiz do projeto.")
        return None

    dest_name = f"harikatha_{utc_timestamp()}.db"
    dest_path = LOCAL_DAILY / dest_name

    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as src:
            with sqlite3.connect(dest_path) as dst:
                dst.execute("PRAGMA journal_mode=WAL;")
                src.backup(dst)

        log.info("Backup atômico criado: %s", dest_path.name)
        gc.collect()
        return dest_path

    except Exception:
        log.exception("Falha ao criar backup atômico")
        return None

def compress_backup(path: Path) -> Path:
    gz_path = path.with_suffix(".db.gz")

    # Compressão
    with path.open("rb") as f_in, gzip.open(gz_path, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)

    log.info("Backup comprimido: %s", gz_path.name)

    # ---- Remoção do .db original (retry) ----
    max_retries = 20  # Aumentado para o Windows não travar
    delay = 1.0       # Delay maior

    for attempt in range(1, max_retries + 1):
        try:
            path.unlink(missing_ok=True)
            log.debug("Arquivo temporário removido: %s", path.name)
            break
        except PermissionError:
            if attempt == max_retries:
                log.warning("Não foi possível remover %s. Mantendo o .db por segurança.", path.name)
                break
            time.sleep(delay)
        except Exception as e:
            log.error("Erro inesperado ao remover %s: %s", path.name, e)
            break

    return gz_path

def manage_retention() -> None:
    now = datetime.now(timezone.utc)
    cutoff_daily = now - timedelta(days=KEEP_DAILY_DAYS)
    
    for f in LOCAL_DAILY.iterdir():
        if f.suffix not in [".gz", ".db"]: continue
        try:
            ts = f.stem.split("_")[1] # Pega timestamp do nome
            # Se for .db.gz, o stem é .db, precisa tratar string
            if "harikatha_" in f.name:
                ts_part = f.name.split("_")[1].split(".")[0]
                file_dt = datetime.strptime(ts_part, "%Y%m%d").replace(tzinfo=timezone.utc)
            else:
                file_dt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        except:
            file_dt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)

        if file_dt < cutoff_daily:
            f.unlink()
            log.info("Removido backup diário antigo: %s", f.name)

def promote_monthly(daily_path: Path) -> None:
    if datetime.now(timezone.utc).day != 1:
        return

    month_tag = datetime.now(timezone.utc).strftime("%Y_%m")
    target = LOCAL_MONTHLY / f"harikatha_MONTHLY_{month_tag}.db.gz"
    shutil.copy2(daily_path, target)
    log.info("Backup mensal criado: %s", target.name)

def sync_cloud() -> None:
    if not RCLONE_REMOTE: return

    rclone_log = BACKUP_ROOT / "rclone_sync.log"
    cmd = [
        "rclone", "sync", str(LOCAL_DAILY), f"{RCLONE_REMOTE}/daily",
        "--log-file", str(rclone_log), "--log-level", "INFO",
        "--transfers", "4"
    ]

    log.info("Iniciando sync cloud...")
    try:
        subprocess.run(cmd, check=True)
        log.info("Sincronização concluída.")
    except Exception as e:
        log.error("Erro no sync: %s", e)

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    log.info("=== Início do ciclo de backup ===")
    ensure_structure()

    backup_path = atomic_sqlite_backup()
    
    if backup_path:
        # CORREÇÃO CRÍTICA: Pausa para o Windows liberar o arquivo antes de ler para comprimir
        time.sleep(2) 
        
        backup_path = compress_backup(backup_path)
        promote_monthly(backup_path)
        manage_retention()
        sync_cloud()
    else:
        log.error("Backup abortado.")

    log.info("=== Processo finalizado ===")