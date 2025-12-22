#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HariKathaAI – Gerenciador de Backups Robusto (versão final)
"""

import os
import sys
import gc
import time
import json
import gzip
import shutil
import logging
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------
# CONFIGURAÇÃO – ajuste apenas se necessário
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent                # pasta onde o script está
DB_PATH = BASE_DIR / "database" / "harikatha.db"
BACKUP_ROOT = BASE_DIR / "backups"

# Sub‑diretórios de backup
LOCAL_DAILY   = BACKUP_ROOT / "daily"
LOCAL_MONTHLY = BACKUP_ROOT / "monthly"

# Política de retenção
KEEP_DAILY_DAYS   = 30   # dias de backups diários
KEEP_MONTHLY_COUNT = 12  # quantos backups mensais manter

# Remote rclone (deixe vazio para desativar a sincronização)
# Exemplo:  "gdrive:HariKathaAI/Backups"   ou   "s3:my-bucket/backups"
RCLONE_REMOTE = "gdrive:HariKathaAI/Backups"

# ----------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------
os.makedirs(BACKUP_ROOT, exist_ok=True)   # garante pasta antes de criar o logger
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
    """Cria diretórios de backup com permissões restritas (700)."""
    for p in (LOCAL_DAILY, LOCAL_MONTHLY):
        p.mkdir(parents=True, exist_ok=True)
        try:
            p.chmod(0o700)          # funciona no Linux; no Windows é ignorado silenciosamente
        except PermissionError:
            pass


def utc_timestamp() -> str:
    """Timestamp ISO‑like sem ':' (compatível com nomes de arquivos)."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def atomic_sqlite_backup() -> Path | None:
    """
    Cria um backup atômico do banco usando sqlite3.backup().
    Usa blocos ``with`` para garantir fechamento imediato das conexões.
    """
    if not DB_PATH.is_file():
        log.error("Banco de dados não encontrado: %s", DB_PATH)
        return None

    dest_name = f"harikatha_{utc_timestamp()}.db"
    dest_path = LOCAL_DAILY / dest_name

    try:
        # Fonte somente‑leitura
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as src:
            # Destino novo
            with sqlite3.connect(dest_path) as dst:
                dst.execute("PRAGMA journal_mode=WAL;")   # opcional, melhora performance
                src.backup(dst)                           # operação atômica

        log.info("Backup atômico criado: %s", dest_path.name)

        # Verifica integridade (opcional)
        with sqlite3.connect(dest_path) as chk_conn:
            chk = chk_conn.execute("PRAGMA integrity_check;").fetchone()[0]
            if chk != "ok":
                log.warning("Backup pode estar corrompido (integrity_check = %s)", chk)

        # Força liberação de handles (especialmente no Windows)
        gc.collect()

        return dest_path

    except Exception:
        log.exception("Falha ao criar backup atômico")
        return None


def compress_backup(path: Path) -> Path:
    """
    GZIP (nível 6) o arquivo ``.db`` e tenta remover o arquivo original.
    No Windows o ``unlink`` pode falhar momentaneamente – faz retry com delay.
    """
    gz_path = path.with_suffix(".db.gz")

    # Compressão
    with path.open("rb") as f_in, gzip.open(gz_path, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)

    log.info("Backup comprimido: %s", gz_path.name)

    # ---- Remoção do .db original (retry) ----
    max_retries = 12
    delay = 0.25   # segundos

    for attempt in range(1, max_retries + 1):
        try:
            path.unlink(missing_ok=True)
            log.debug("Arquivo temporário removido: %s", path.name)
            break
        except PermissionError:
            if attempt == max_retries:
                log.warning(
                    "Não foi possível remover %s após %d tentativas. "
                    "Mantendo o .db por segurança.",
                    path.name, max_retries,
                )
                break
            log.debug(
                "Tentativa %d/%d: arquivo ainda em uso (%s). Aguardando %.2fs...",
                attempt, max_retries, path.name, delay,
            )
            time.sleep(delay)
        except Exception as e:
            log.error("Erro inesperado ao remover %s: %s", path.name, e)
            break

    return gz_path


def manage_retention() -> None:
    """Aplica política de retenção diária e mensal."""
    now = datetime.now(timezone.utc)

    # ---------- DIÁRIOS ----------
    cutoff_daily = now - timedelta(days=KEEP_DAILY_DAYS)
    for f in LOCAL_DAILY.iterdir():
        if f.suffix != ".gz":
            continue
        try:
            ts = f.stem.split("_")[1]          # harikatha_YYYYMMDD_HHMMSS.db.gz
            file_dt = datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            file_dt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)

        if file_dt < cutoff_daily:
            f.unlink()
            log.info("Removido backup diário antigo: %s", f.name)

    # ---------- MENSAIS ----------
    monthly = sorted(
        (p for p in LOCAL_MONTHLY.iterdir() if p.suffix == ".gz"),
        key=lambda p: p.name,
    )
    if len(monthly) > KEEP_MONTHLY_COUNT:
        for old in monthly[:-KEEP_MONTHLY_COUNT]:
            old.unlink()
            log.info("Removido backup mensal excedente: %s", old.name)


def promote_monthly(daily_path: Path) -> None:
    """No dia 1 do mês copia o backup diário para a pasta mensal."""
    if datetime.now(timezone.utc).day != 1:
        return

    month_tag = datetime.now(timezone.utc).strftime("%Y_%m")
    target = LOCAL_MONTHLY / f"harikatha_MONTHLY_{month_tag}.db.gz"
    shutil.copy2(daily_path, target)
    log.info("Backup mensal criado: %s", target.name)


def sync_cloud() -> None:
    """Sincroniza a pasta daily com a nuvem via rclone (se configurado)."""
    if not RCLONE_REMOTE:
        log.debug("RCLONE_REMOTE vazio → sincronização desativada.")
        return

    rclone_log = BACKUP_ROOT / "rclone_sync.log"

    cmd = [
        "rclone",
        "sync",
        str(LOCAL_DAILY),
        f"{RCLONE_REMOTE}/daily",
        "--log-file",
        str(rclone_log),
        "--log-level",
        "INFO",
        "--stats",
        "30s",
        "--timeout",
        "10m",
        "--retries",
        "5",
        "--low-level-retries",
        "5",
        "--transfers",
        "8",
    ]

    log.info("Iniciando sync cloud: %s", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        log.info("Sincronização concluída com sucesso.")
    except FileNotFoundError:
        log.error("rclone não encontrado no PATH. Instale ou ajuste RCLONE_REMOTE.")
    except subprocess.CalledProcessError as e:
        log.error(
            "Sync falhou (rc=%s). Consulte %s para detalhes.",
            e.returncode,
            rclone_log,
        )
    except Exception:
        log.exception("Erro inesperado ao sincronizar com a nuvem.")


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    log.info("=== Início do ciclo de backup ===")
    ensure_structure()

    backup_path = atomic_sqlite_backup()
    if backup_path:
        backup_path = compress_backup(backup_path)
        promote_monthly(backup_path)
        manage_retention()
        sync_cloud()
    else:
        log.error("Backup abortado – nada foi criado.")

    log.info("=== Processo finalizado ===")
