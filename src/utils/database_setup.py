#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
setup_database.py

Cria e inicializa o banco SQLite usado pelo projeto HariKatha‑3.0.
Versão: v6.5 (Arquitetura Raiz-Folha V3.0).

Autor: equipe HariKatha
"""

import os
import sqlite3
import logging

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
DB_FOLDER = "database"
DB_NAME = "harikatha.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("HariKathaAI_v6.5")

# ==============================================================================
# FUNÇÕES DE CRIAÇÃO
# ==============================================================================

def setup_database() -> None:
    """Cria o diretório, conecta ao SQLite e cria todas as tabelas."""
    os.makedirs(DB_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    # Otimizações de performance e integridade
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    cur = conn.cursor()
    logger.info("🏗️  Construindo HariKathaAI v6.5 (Schema V3.0)...")

    # -------------------------------------------------------------------------
    # 1. Apoio e aprendizado
    # -------------------------------------------------------------------------
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS languages (
            code TEXT PRIMARY KEY CHECK (length(code) BETWEEN 2 AND 3),
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS learning_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrong_term TEXT UNIQUE NOT NULL,
            correct_term TEXT NOT NULL,
            correction_type TEXT DEFAULT 'PHONETIC',
            confidence_score REAL DEFAULT 1.0,
            is_active_rule INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            language_code TEXT REFERENCES languages(code)
        );
    """)

    # -------------------------------------------------------------------------
    # 2. Lectures (Conteúdo Base)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youtube_url TEXT UNIQUE NOT NULL,
            youtube_id TEXT UNIQUE,
            file_hash TEXT UNIQUE,
            lecture_title TEXT NOT NULL,
            lecture_date DATETIME NOT NULL,
            current_state TEXT NOT NULL DEFAULT 'NEW'
                CHECK (current_state IN ('NEW','HARVESTED','PREPROCESSED',
                                       'TRANSCRIBED','AUDITED','PUBLISHED',
                                       'FAILED','ARCHIVED')),
            duration_seconds REAL CHECK (duration_seconds >= 0),
            path_cover_image TEXT,
            
            -- Auditoria e Sincronia
            audit_status TEXT DEFAULT 'PENDING',
            sync_diff_avg REAL,
            cut_mode TEXT,
            kirtan_offset_seconds REAL DEFAULT 0.0,
            retry_count INTEGER DEFAULT 0,
            
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # -------------------------------------------------------------------------
    # 3. Media Assets
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS media_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL
                CHECK (asset_type IN ('AUDIO','PDF','SRT','COVER')),
            file_path TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
        );
    """)

    # -------------------------------------------------------------------------
    # 4. Pipeline Jobs (Orquestração)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            lecture_id INTEGER,
            status TEXT NOT NULL DEFAULT 'PENDING',
            started_at DATETIME,
            finished_at DATETIME,
            error_message TEXT,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
        );
    """)

    # -------------------------------------------------------------------------
    # 5. Auditoria IA (Custos e Logs)
    # -------------------------------------------------------------------------
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS ai_audit_logs (
            audit_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id          INTEGER,
            book_id             INTEGER,
            job_id              INTEGER,
            model_name          TEXT    NOT NULL,
            request_hash        TEXT    NOT NULL,
            prompt_raw          TEXT    NOT NULL,
            response_raw        TEXT,
            input_tokens        INTEGER NOT NULL,
            output_tokens       INTEGER,
            estimated_cost_usd  REAL    NOT NULL,
            status_code         TEXT    NOT NULL,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(request_hash, model_name)
        );
    """)

    # -------------------------------------------------------------------------
    # 6. BIBLIOTECA (ARQUITETURA V3.0 - RAIZ/FOLHA)
    # -------------------------------------------------------------------------
    
    # 6.1 Livros (Faltava no seu script anterior)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS library_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acronym TEXT UNIQUE NOT NULL,
            book_title TEXT NOT NULL,
            label_l1 TEXT, -- Ex: Canto
            label_l2 TEXT, -- Ex: Capítulo
            label_l3 TEXT, -- Ex: Verso
            language_default TEXT DEFAULT 'sa'
        );
    """)

    # 6.2 Índice (Esqueleto)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS library_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            canonical_id TEXT UNIQUE, -- ex: BRS_1.1.1
            num_1 INTEGER,
            num_2 INTEGER,
            num_3 INTEGER,
            page_number INTEGER,
            FOREIGN KEY(book_id) REFERENCES library_books(id)
        );
    """)

    # 6.3 Texto Raiz (Sânscrito/Bengali) - 1:1 com Índice
    cur.execute("""
        CREATE TABLE IF NOT EXISTS library_root_text (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_id INTEGER UNIQUE,  -- UNIQUE garante apenas 1 original por verso
            primary_script TEXT,      -- Devanagari ou Bengali
            transliteration TEXT,     -- IAST
            FOREIGN KEY(index_id) REFERENCES library_index(id)
        );
    """)

    # 6.4 Traduções (Inglês, PT, etc) - 1:N com Índice
    cur.execute("""
        CREATE TABLE IF NOT EXISTS library_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_id INTEGER,
            language_code TEXT,       -- 'en', 'pt'
            translator TEXT,          -- 'WisdomLib (1)', 'AI_Gemini', 'Swami X'
            text_body TEXT,
            FOREIGN KEY(index_id) REFERENCES library_index(id),
            
            -- Chave composta: Um tradutor só pode ter uma versão por língua para um verso
            UNIQUE(index_id, language_code, translator)
        );
    """)

    # -------------------------------------------------------------------------
    # 7. Tabelas de Saída (Factory)
    # -------------------------------------------------------------------------
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS lecture_verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            library_index_id INTEGER NOT NULL,
            timestamp_seconds REAL NOT NULL,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE,
            FOREIGN KEY (library_index_id) REFERENCES library_index(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            slug TEXT UNIQUE,
            content_html TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
        );
    """)

    # -------------------------------------------------------------------------
    # 8. Índices e Triggers
    # -------------------------------------------------------------------------
    logger.info("⚡ Otimizando índices...")
    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_lib_canon ON library_index (canonical_id);
        CREATE INDEX IF NOT EXISTS idx_lectures_date ON lectures (lecture_date DESC);
        
        CREATE TRIGGER IF NOT EXISTS trg_lectures_update
        AFTER UPDATE ON lectures
        BEGIN
            UPDATE lectures SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    """)

    # -------------------------------------------------------------------------
    # 9. Dados Iniciais
    # -------------------------------------------------------------------------
    seed_initial_knowledge(conn)

    conn.commit()
    conn.close()
    logger.info("✅ HariKathaAI v6.5 configurado com sucesso!")


def seed_initial_knowledge(conn: sqlite3.Connection) -> None:
    """Insere dados estáticos iniciais (idiomas, regras e livros)."""
    cur = conn.cursor()
    logger.info("🌱 Semeando conhecimento inicial...")

    # Idiomas
    cur.executemany(
        "INSERT OR IGNORE INTO languages (code, description) VALUES (?, ?);",
        [("pt", "Português"), ("en", "English"), ("sa", "Sânscrito"), ("bn", "Bengali")]
    )

    # Livros (Estrutura da biblioteca)
    livros = [
        ("SB", "Śrīmad-Bhāgavatam", "Canto", "Capítulo", "Verso", "sa"),
        ("BRS", "Bhakti-rasāmṛta-sindhu", "Vibhaga", "Lahari", "Verso", "sa"),
        ("CC", "Śrī Caitanya-caritāmṛta", "Lila", "Capítulo", "Verso", "bn"),
        ("UN", "Ujjvala-nīlamaṇi", None, "Prakarana", "Verso", "sa"),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO library_books
        (acronym, book_title, label_l1, label_l2, label_l3, language_default)
        VALUES (?, ?, ?, ?, ?, ?);
    """, livros)
    
    logger.info("✅ Seed concluído.")

if __name__ == "__main__":
    setup_database()