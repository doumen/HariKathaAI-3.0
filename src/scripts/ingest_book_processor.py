#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ingest Book Processor - HariKathaAI
-----------------------------------
Script responsável por ingerir textos sagrados (Shastras) no banco de dados.
Utiliza o SmartAIWrapper v6.7 para tradução/análise com auditoria e controle de custos.

Fluxo:
1. Cria/Recupera o Livro na tabela library_books.
2. Cria um JOB de ingestão em pipeline_jobs.
3. Itera sobre os versos/seções do texto.
4. Envia para IA via Wrapper (com cache e auditoria).
5. Salva o resultado em library_content.
"""

import sys
import sqlite3
import logging
import json
import time
from pathlib import Path

# Ajuste de path para encontrar o utils/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / "src" / "utils"))

from smart_ai_wrapper import SmartAIWrapper  # Assumindo que você salvou a v6.7 lá

# Configurações
DB_PATH = BASE_DIR / "database" / "harikatha.db"
logger = logging.getLogger("IngestProcessor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- MOCK DO TEXTO (Em produção, isso viria de um .txt ou .md) ---
UJJVALA_RAW_TEXT = [
    {
        "ref": "UN 1.1",
        "sanskrit": "namaḥ śrī-kṛṣṇa-candrāya\nnikhilābhīṣṭa-siddhaye...",
        "prompt_context": "Traduza este verso invocatório do Ujjvala-nilamani para Português e forneça um breve significado."
    },
    {
        "ref": "UN 1.2",
        "sanskrit": "mukhya-rasa-kadambasya\nmūrtir ekā virājate...",
        "prompt_context": "Analise gramaticalmente e traduza o verso 1.2 do Ujjvala-nilamani."
    }
]

class BookIngestor:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.wrapper = SmartAIWrapper(db_path=DB_PATH)
        self.book_id = None
        self.job_id = None

    def setup_book(self):
        """Garante que o livro existe no catálogo."""
        logger.info("📚 Configurando livro: Ujjvala-nīlamaṇi")
        cursor = self.conn.cursor()
        
        # Inserir ou recuperar ID
        cursor.execute("""
            INSERT OR IGNORE INTO library_books 
            (acronym, book_title, label_l1, label_l2, label_l3, language_default)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("UN", "Ujjvala-nīlamaṇi", None, "Prakarana", "Verso", "sa"))
        self.conn.commit()

        cursor.execute("SELECT id FROM library_books WHERE acronym = 'UN'")
        self.book_id = cursor.fetchone()[0]
        logger.info(f"✅ Livro configurado. ID: {self.book_id}")

    def start_job(self):
        """Registra o início do trabalho no pipeline."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO pipeline_jobs (job_type, status, started_at)
            VALUES ('INGEST_BOOK', 'RUNNING', CURRENT_TIMESTAMP)
        """)
        self.job_id = cursor.lastrowid
        self.conn.commit()
        logger.info(f"⚙️ Job {self.job_id} iniciado.")

    def mock_provider(self, prompt: str, model: str) -> str:
        """
        Simula a resposta da IA para testes sem custo real.
        Em produção, substitua por: return genai.GenerativeModel(model).generate_content(prompt).text
        """
        time.sleep(0.5) # Simula latência
        return f"[IA TRANSLATION] Análise do verso '{prompt[:30]}...' realizada com sucesso.\nSignificado: A doçura de Krishna é suprema."

    def process_content(self):
        """Loop principal de ingestão."""
        cursor = self.conn.cursor()
        
        for item in UJJVALA_RAW_TEXT:
            ref = item['ref']
            raw_text = item['sanskrit']
            
            logger.info(f"🔄 Processando {ref}...")

            # 1. Cria o índice (GPS do verso)
            # Extrai números do ref (ex: UN 1.1 -> num_1=1, num_2=1)
            # Simplificação para o exemplo:
            parts = ref.split()[-1].split('.')
            n1 = int(parts[0])
            n2 = int(parts[1])

            try:
                cursor.execute("""
                    INSERT INTO library_index (book_id, canonical_id, num_1, num_2, page_number)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.book_id, ref, n1, n2, 0))
                index_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # Se já existe, recupera o ID
                cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (ref,))
                index_id = cursor.fetchone()[0]

            # 2. Chama a IA via Wrapper (Com Auditoria)
            full_prompt = f"Texto: {raw_text}\nContexto: {item['prompt_context']}"
            
            ai_response = self.wrapper.call_ai(
                prompt=full_prompt,
                model="gemini-1.5-flash",
                book_id=self.book_id,
                job_id=self.job_id,
                provider_func=self.mock_provider # <--- INJEÇÃO DA FUNÇÃO REAL AQUI
            )

            if ai_response:
                # 3. Salva o conteúdo gerado
                cursor.execute("""
                    INSERT INTO library_content (index_id, content_type, language_code, text_body, version)
                    VALUES (?, 'TRANSLATION', 'pt', ?, 1)
                """, (index_id, ai_response))
                self.conn.commit()
                logger.info(f"💾 {ref} salvo com sucesso.")
            else:
                logger.warning(f"⚠️ {ref} pulado (Bloqueio de custo ou Erro).")

    def finish_job(self):
        """Marca o job como concluído."""
        self.conn.execute("""
            UPDATE pipeline_jobs SET status = 'SUCCESS', finished_at = CURRENT_TIMESTAMP 
            WHERE job_id = ?
        """, (self.job_id,))
        self.conn.commit()
        self.conn.close()
        logger.info("🏁 Ingestão concluída.")

if __name__ == "__main__":
    ingestor = BookIngestor()
    try:
        ingestor.setup_book()
        ingestor.start_job()
        ingestor.process_content()
        ingestor.finish_job()
    except Exception as e:
        logger.error(f"❌ Falha fatal: {e}")
        # Em caso de erro real, atualizar job para FAILED
        if ingestor.job_id:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("UPDATE pipeline_jobs SET status = 'FAILED', error_message = ? WHERE job_id = ?", (str(e), ingestor.job_id))