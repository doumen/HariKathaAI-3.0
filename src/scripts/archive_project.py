#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
archive_project.py
Empacota os artefatos de ingestão (PDF + Scripts + Docs) e envia para o Google Drive.
"""

import os
import zipfile
import subprocess
import logging
from datetime import datetime

# Configuração
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCHIVE_DIR = os.path.join(BASE_DIR, "archives")
RCLONE_REMOTE = "gdrive:HariKathaAI/Sources/Slokamrtam"  # Pasta separada para fontes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def create_archive():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_filename = os.path.join(ARCHIVE_DIR, f"Slokamrtam_Ingestion_Pack_{timestamp}.zip")
    
    # Arquivos para salvar (Caminhos relativos à raiz do projeto)
    files_to_save = [
        "Sri Slokamrtam Cinmaya v1.0.qxp - Sri_Slokamritam.pdf",  # O PDF Original
        "src/ingestion/miner_slokamrtam.py",                      # O Minerador V23
        "src/scripts/fix_slk_1_0.py",                             # Fix 1.0
        "src/scripts/final_patch.py",                             # Patch Manual
        "src/scripts/final_cleanup.py",                           # Limpeza Final
        "docs/INGESTION_LOG_SLOKAMRTAM.md",                       # A Documentação
        "src/ingestion/audit_slokamrtam.py"                       # O Auditor
    ]

    logging.info(f"📦 Criando arquivo: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_rel_path in files_to_save:
            abs_path = os.path.join(BASE_DIR, file_rel_path)
            if os.path.exists(abs_path):
                zipf.write(abs_path, arcname=file_rel_path)
                logging.info(f"   Adicionado: {file_rel_path}")
            else:
                logging.warning(f"   ⚠️ Arquivo não encontrado (pulei): {file_rel_path}")
                
    return zip_filename

def upload_to_drive(file_path):
    if not os.path.exists(file_path):
        return

    file_name = os.path.basename(file_path)
    logging.info(f"☁️ Enviando {file_name} para {RCLONE_REMOTE}...")
    
    cmd = [
        "rclone", "copy", file_path, RCLONE_REMOTE, 
        "--stats", "10s"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logging.info("✅ Upload concluído com sucesso!")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Erro no upload: {e}")

if __name__ == "__main__":
    # 1. Cria a documentação se não existir (dummy) apenas para não quebrar
    doc_path = os.path.join(BASE_DIR, "docs", "INGESTION_LOG_SLOKAMRTAM.md")
    if not os.path.exists(os.path.dirname(doc_path)):
        os.makedirs(os.path.dirname(doc_path))
    
    # 2. Gera o Zip
    zip_file = create_archive()
    
    # 3. Sobe pro Drive
    upload_to_drive(zip_file)