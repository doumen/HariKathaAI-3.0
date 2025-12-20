#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HariKathaAI – Gerenciador de Backups Robusto (versão final)
"""

import os
import sqlite3
import shutil
import subprocess
import logging
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -------------------------- CONFIGURAÇÃO --------------------------
BASE_DIR       = Path(__file__).resolve().parent
DB_PATH        = BASE_DIR / "database" / "harikatha.db"
BACKUP_ROOT    = BASE_DIR / "backups"

LOCAL_DAILY    = BACKUP_ROOT / "daily"
LOCAL_MONTHLY  = BACKUP_ROOT / "monthly"

KEEP_DAILY_DAYS   = 30          # dias de backups diários
KEEP_MONTHLY_COUNT = 12         # número de backups mensais a manter

# Deixe vazio para desativar a sincronização cloud
RCLONE_REMOTE = "gdrive:HariKathaAI/Backups"

# -------------------------- LOGGING -----------------------------
os.makedirs(BACKUP_ROOT, exist_ok=True)               # garante pasta antes do logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BACKUP_ROOT / "backup.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("backup")

# -------------------------- FUNÇÕES -----------------------------

def ensure_structure() -> None:
    """Cria diretórios de backup com permissões restritas."""
    for p in (LOCAL_DAILY, LOCAL_MONTHLY):
        p.mkdir(parents=True, exist_ok=True)
        p.chmod(0o700)

def utc_timestamp() -> str:
    """String ISO‑like sem ':' – compatível com nomes de arquivos."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def atomic_sqlite_backup() -> Path | None:
    """Copia o banco de forma atômica usando sqlite3.backup()."""
    if not DB_PATH.is_file():
        log.error("Banco de dados não encontrado: %s", DB_PATH)
        return None

    dest_name = f"harikatha_{utc_timestamp()}.db"
    dest_path = LOCAL_DAILY / dest_name

    try:
        src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        dst = sqlite3.connect(dest_path)

        with dst:
            src.backup(dst)                  # operação atômica

        src.close()
        dst.close()
        log.info("Backup atômico criado: %s", dest_path.name)

        # ---------- integridade ----------
        chk = sqlite3.connect(dest_path).execute("PRAGMA integrity_check;").fetchone()[0]
        if chk != "ok":
            log.warning("Backup pode estar corrompido (integrity_check = %s)", chk)

        return dest_path
    except Exception:
        log.exception("Falha ao criar backup")
        return None

def compress_backup(path: Path) -> Path:
    """GZIP (nível 6) e remove o .db original."""
    gz_path = path.with_suffix(".db.gz")
    with path.open("rb") as f_in, gzip.open(gz_path, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)
    path.unlink()
    log.info("Backup comprimido: %s", gz_path.name)
    return gz_path

def manage_retention() -> None:
    """Aplica política de retenção diária e mensal."""
    now = datetime.now(timezone.utc)

    # ---- Diários ----
    cutoff_daily = now - timedelta(days=KEEP_DAILY_DAYS)
    for f in LOCAL_DAILY.iterdir():
        if f.suffix != ".gz":
            continue
        # extrai timestamp do nome: harikatha_20251220_023500.db.gz
        try:
            ts = f.stem.split("_")[1]
            file_dt = datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            file_dt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)

        if file_dt < cutoff_daily:
            f.unlink()
            log.info("Removido backup diário antigo: %s", f.name)

    # ---- Mensais ----
    monthly_files = sorted(
        [p for p in LOCAL_MONTHLY.iterdir() if p.suffix == ".gz"],
        key=lambda x: x.name
    )
    if len(monthly_files) > KEEP_MONTHLY_COUNT:
        for old in monthly_files[:-KEEP_MONTHLY_COUNT]:
            old.unlink()
            log.info("Removido backup mensal excedente: %s", old.name)

def promote_monthly(daily_path: Path) -> None:
    """No dia 1, copia o backup diário para a pasta monthly."""
    if datetime.now(timezone.utc).day != 1:
        return
    month_tag = datetime.now(timezone.utc).strftime("%Y_%m")
    target = LOCAL_MONTHLY / f"harikatha_MONTHLY_{month_tag}.db.gz"
    shutil.copy2(daily_path, target)
    log.info("Backup mensal criado: %s", target.name)

def sync_cloud() -> None:
    """Sincroniza a pasta daily com a nuvem via rclone (se configurado)."""
    if not RCLONE_REMOTE:
        return

    cmd = ["rclone", "sync", str(LOCAL_DAILY), f"{RCLONE_REMOTE}/daily"]
    log.info("Iniciando sync cloud: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        log.info("Sincronização cloud concluída com sucesso.")
    except subprocess.CalledProcessError as e:
        log.warning("Sync falhou (rc=%s): %s", e.returncode, e.stderr.strip())
    except FileNotFoundError:
        log.error("rclone não encontrado no PATH. Instale ou ajuste RCLONE_REMOTE.")
    except Exception:
        log.exception("Erro inesperado ao sincronizar com a nuvem.")

# -------------------------- MAIN -------------------------------
if __name__ == "__main__":
    log.info("=== Início do ciclo de backup ===")
    ensure_structure()

    backup_path = atomic_sqlite_backup()
    if backup_path:
        backup_path = compress_backup(backup_path)
        promote_monthly(backup_path)
        manage_retention()
        sync_cloud()

    log.info("=== Processo finalizado ===")
