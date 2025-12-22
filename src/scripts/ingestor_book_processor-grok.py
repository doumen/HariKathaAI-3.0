#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingest Book Processor - HariKathaAI v6.5 Final
-----------------------------------
Script responsável por ingerir textos sagrados (Shastras) no banco de dados.
Utiliza o SmartAIWrapper v6.7 para tradução/análise com auditoria e controle de custos.
Fluxo:
1. Cria/Recupera o Livro na tabela library_books.
2. Cria um JOB de ingestão em pipeline_jobs.
3. Itera sobre os versos/seções do texto (de JSON ou arquivo).
4. Envia para IA via Wrapper (com cache e auditoria).
5. Salva o resultado em library_content.
Melhorias na versão final:
- Parsing robusto de refs com regex
- Tratamento de falhas no loop (continue em erro)
- argparse para input de arquivo JSON
- Opcional: integração com PyMuPDF para PDF (comente se não precisar)
- Atualização de job em erro
"""
import sys
import sqlite3
import logging
import json
import argparse
import re
from pathlib import Path

# Ajuste de path para encontrar o utils/ (assumindo estrutura de projeto)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "utils"))  # Ajuste se o wrapper estiver em outro lugar
from smart_ai_wrapper import SmartAIWrapper  # Assumindo que você salvou a v6.7 lá

# Configurações
DB_PATH = BASE_DIR / "database" / "harikatha.db"
logger = logging.getLogger("IngestProcessor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class BookIngestor:
    def __init__(self, book_acronym: str, book_title: str, input_file: str = None):
        self.conn = sqlite3.connect(DB_PATH)
        self.wrapper = SmartAIWrapper(db_path=DB_PATH)
        self.book_acronym = book_acronym
        self.book_title = book_title
        self.book_id = None
        self.job_id = None
        self.raw_text = self._load_input(input_file)

    def _load_input(self, input_file: str) -> list:
        """Carrega o input de arquivo JSON ou usa mock."""
        if input_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning("Usando mock UJJVALA_RAW_TEXT (para testes)")
            return [
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

    def setup_book(self):
        """Garante que o livro existe no catálogo."""
        logger.info(f"📚 Configurando livro: {self.book_title}")
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO library_books
            (acronym, book_title, label_l1, label_l2, label_l3, language_default)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.book_acronym, self.book_title, None, "Prakarana", "Verso", "sa"))
        self.conn.commit()
        
        cursor.execute("SELECT id FROM library_books WHERE acronym = ?", (self.book_acronym,))
        result = cursor.fetchone()
        if result:
            self.book_id = result[0]
            logger.info(f"✅ Livro configurado. ID: {self.book_id}")
        else:
            raise ValueError(f"Livro '{self.book_acronym}' não encontrado após insert.")

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
        time.sleep(0.5)  # Simula latência
        return f"[IA TRANSLATION] Análise do verso '{prompt[:30]}...' realizada com sucesso.\nSignificado: A doçura de Krishna é suprema."

    def process_content(self):
        """Loop principal de ingestão."""
        cursor = self.conn.cursor()
        
        for item in self.raw_text:
            ref = item['ref']
            raw_text = item['sanskrit']
            
            logger.info(f"🔄 Processando {ref}...")
            
            # 1. Parsing robusto do ref com regex (lida com 1.1, 1.1-3, Invocatório)
            match = re.match(r'([A-Za-z0-9]+)\s*(\d+)?(?:\.(\d+))?-(?:\d+)?', ref)
            n1 = int(match.group(2)) if match.group(2) else 0
            n2 = int(match.group(3)) if match.group(3) else 0
            n3 = 0  # Para ranges, pode expandir depois
            
            # 2. Cria o índice (GPS do verso)
            try:
                cursor.execute("""
                    INSERT INTO library_index (book_id, canonical_id, num_1, num_2, num_3, page_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (self.book_id, ref, n1, n2, n3, item.get('page', 0)))
                index_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # Se já existe, recupera o ID
                cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (ref,))
                result = cursor.fetchone()
                if result:
                    index_id = result[0]
                else:
                    logger.error(f"Falha ao recuperar index_id para {ref}")
                    continue
            
            # 3. Chama a IA via Wrapper (Com Auditoria)
            full_prompt = f"Texto: {raw_text}\nContexto: {item['prompt_context']}"
            
            try:
                ai_response = self.wrapper.call_ai(
                    prompt=full_prompt,
                    model="gemini-1.5-flash",
                    operation_type='INGEST_VERSE',  # Adicionei para relatórios
                    book_id=self.book_id,
                    job_id=self.job_id,
                    provider_func=self.mock_provider  # Substitua pela função real da IA
                )
                if ai_response:
                    # 4. Salva o conteúdo gerado
                    cursor.execute("""
                        INSERT INTO library_content (index_id, content_type, language_code, text_body, version)
                        VALUES (?, 'TRANSLATION', 'pt', ?, 1)
                    """, (index_id, ai_response))
                    self.conn.commit()
                    logger.info(f"💾 {ref} salvo com sucesso.")
                else:
                    logger.warning(f"⚠️ {ref} pulado (Bloqueio de custo ou Erro).")
                    continue  # Continua o loop em erro
            except Exception as e:
                logger.error(f"Falha ao processar {ref}: {e}")
                continue  # Continua o loop em erro geral
    
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
    parser = argparse.ArgumentParser(description="Ingestor de Livros para HariKathaAI")
    parser.add_argument("--input_file", help="Caminho para o JSON do livro (opcional, usa mock se vazio)")
    args = parser.parse_args()
    
    ingestor = BookIngestor(book_acronym="UN", book_title="Ujjvala-nīlamaṇi", input_file=args.input_file)
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