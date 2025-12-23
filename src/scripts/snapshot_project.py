#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
snapshot_project.py
Cria um PACOTE COMPLETO (Código + Banco + Docs) e envia para o Google Drive.
Isso garante a reprodutibilidade total do projeto no futuro.
"""

import os
import zipfile
import subprocess
import logging
from datetime import datetime

# --- Configurações ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
# Pasta no Drive específica para versões congeladas
RCLONE_REMOTE = "gdrive:HariKathaAI/Releases/v1.0_Slokamrtam_Gold"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M")

def create_requirements_file():
    """Gera o requirements.txt atualizado."""
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    logging.info("📝 Gerando requirements.txt...")
    try:
        with open(req_path, "w") as f:
            subprocess.run(["pip", "freeze"], stdout=f)
    except Exception as e:
        logging.warning(f"⚠️ Não foi possível gerar requirements.txt: {e}")
    return req_path

def create_zip_snapshot():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    zip_name = f"HariKathaAI_Snapshot_{get_timestamp()}.zip"
    zip_path = os.path.join(SNAPSHOT_DIR, zip_name)
    
    logging.info(f"📦 Compactando o projeto em: {zip_name}")
    
    # Lista de pastas e arquivos para incluir
    dirs_to_include = ["src", "docs", "database"] # Inclui o banco!
    files_to_include = ["requirements.txt", "README.md", "Sri Slokamrtam Cinmaya v1.0.qxp - Sri_Slokamritam.pdf"]
    
    # Pastas para ignorar (lixo)
    dirs_to_ignore = ["__pycache__", ".git", ".vscode", "venv", "env", "backups", "snapshots", "archives"]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 1. Adiciona arquivos soltos da raiz
        for file in files_to_include:
            abs_path = os.path.join(BASE_DIR, file)
            if os.path.exists(abs_path):
                zipf.write(abs_path, arcname=file)
                
        # 2. Adiciona diretórios recursivamente
        for folder in dirs_to_include:
            folder_path = os.path.join(BASE_DIR, folder)
            if not os.path.exists(folder_path):
                continue
                
            for root, dirs, files in os.walk(folder_path):
                # Remove pastas ignoradas da travessia
                dirs[:] = [d for d in dirs if d not in dirs_to_ignore]
                
                for file in files:
                    if file.endswith(".pyc") or file == ".DS_Store": continue
                    
                    abs_file_path = os.path.join(root, file)
                    # Caminho relativo dentro do ZIP
                    rel_path = os.path.relpath(abs_file_path, BASE_DIR)
                    zipf.write(abs_file_path, arcname=rel_path)
    
    logging.info(f"✅ Snapshot criado: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    return zip_path

def upload_to_drive(file_path):
    if not os.path.exists(file_path): return

    file_name = os.path.basename(file_path)
    logging.info(f"☁️ Enviando para o Google Drive: {RCLONE_REMOTE}...")
    
    cmd = [
        "rclone", "copy", file_path, RCLONE_REMOTE, 
        "--stats", "5s", "--progress"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        logging.info("🚀 Upload concluído com sucesso! Projeto preservado.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Erro no upload: {e}")

if __name__ == "__main__":
    # 1. Gera lista de dependências
    create_requirements_file()
    
    # 2. Cria o Zipão
    snapshot_zip = create_zip_snapshot()
    
    # 3. Sobe para a nuvem
    upload_to_drive(snapshot_zip)