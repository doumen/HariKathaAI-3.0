#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import logging
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
DB_FOLDER = "database"
DB_NAME = "harikatha.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HariKathaAI_v6.4")

def setup_database():
    os.makedirs(DB_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    logger.info("🏗️  Construindo HariKathaAI v6.4 Final Build...")

    # 1. APOIO E APRENDIZADO
    cursor.executescript("""
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
        is_active_rule BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. LECTURES (Com suporte Multimídia e Auditoria)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        youtube_url TEXT UNIQUE NOT NULL,
        youtube_id TEXT UNIQUE,
        file_hash TEXT UNIQUE,
        lecture_title TEXT NOT NULL,
        lecture_date DATETIME NOT NULL,
        current_state TEXT NOT NULL DEFAULT 'NEW' 
            CHECK (current_state IN ('NEW','HARVESTED','PREPROCESSED','TRANSCRIBED','AUDITED','PUBLISHED','FAILED','ARCHIVED')),
        duration_seconds REAL,
        
        -- Campos de Produção de Mídia
        path_audio_master TEXT,
        path_pdf_fascicle TEXT,
        path_srt_zip TEXT,
        path_cover_image TEXT,
        
        -- Campos de Sincronia e Auditoria
        audit_status TEXT DEFAULT 'PENDING',
        sync_diff_avg REAL,
        cut_mode TEXT,
        kirtan_offset_seconds REAL DEFAULT 0.0,
        retry_count INTEGER DEFAULT 0,
        
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. ORQUESTRAÇÃO (Pipeline Jobs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pipeline_jobs (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_type TEXT CHECK (job_type IN ('DOWNLOAD','OCR','TRANSCRIBE','ALIGN','PDF_GEN','PUBLISH')),
        lecture_id INTEGER,
        status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING','RUNNING','SUCCESS','FAILED')),
        started_at DATETIME,
        finished_at DATETIME,
        error_message TEXT,
        FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
    );
    """)

    # 4. BIBLIOTECA (Taxonomia WisdomLib)
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS library_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acronym TEXT UNIQUE NOT NULL,
        book_title TEXT NOT NULL,
        label_l1 TEXT, label_l2 TEXT, label_l3 TEXT,
        language_default TEXT NOT NULL REFERENCES languages(code)
    );

    CREATE TABLE IF NOT EXISTS library_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        canonical_id TEXT UNIQUE NOT NULL,
        num_1 INTEGER, num_2 INTEGER, num_3 INTEGER,
        page_number INTEGER NOT NULL,
        FOREIGN KEY (book_id) REFERENCES library_books(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS library_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_id INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        language_code TEXT NOT NULL REFERENCES languages(code),
        text_body TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        FOREIGN KEY (index_id) REFERENCES library_index(id) ON DELETE CASCADE
    );
    """)

    # 5. TABELAS DE SAÍDA (Factory)
    cursor.executescript("""
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
        FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
    );
    """)

    create_indexes(cursor)
    seed_initial_knowledge(conn)
    
    conn.commit()
    conn.close()
    logger.info("✅ HariKathaAI v6.4 Final Build Configurado!")

def create_indexes(cursor):
    """Índices estratégicos para performance e dashboards."""
    logger.info("⚡ Criando índices de performance...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_state ON lectures (current_state)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_date ON lectures (lecture_date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON pipeline_jobs (status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lib_order ON library_index (book_id, num_1, num_2, num_3)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lib_canon ON library_index (canonical_id)")

def seed_initial_knowledge(conn):
    """Seed completo com o Cérebro Fonético e Shastras."""
    cursor = conn.cursor()
    logger.info("🌱 Semeando conhecimento inicial (Enterprise Seed)...")
    
    # Idiomas
    cursor.executemany("INSERT OR IGNORE INTO languages (code, description) VALUES (?,?)", 
                       [('pt','Português'), ('en','English'), ('sa','Sânscrito'), ('bn','Bengali')])

    # REGRAS FONÉTICAS (Lookahead & Editorial)
    regras = [
        (r"(Luta|Lota|Loota)\s*(Svitav|Svetav|feet\s*of)", "lotus feet of", "PHONETIC"),
        (r"(om\s+)?(Vishnupada)[\s\S]{1,40}?(?=\bBhaktivedanta|\bVana|\bNarayan)", "om vishnupada astottara-sata Sri Srimad ", "EDITORIAL"),
        (r"\b(Sri|Srila)\s*(Ramana|Romana|Vana)\s*Maharaj", "Bhaktivedanta Srila Vamana Gosvami Maharaja", "EDITORIAL"),
        (r"(Devotion\s*(and|&)\s*service[\.,\s]*){2,}", "Devotional service. ", "EDITORIAL")
    ]
    cursor.executemany("INSERT OR IGNORE INTO learning_corrections (wrong_term, correct_term, correction_type) VALUES (?,?,?)", regras)

    # LIVROS
    livros = [
        ("SB", "Śrīmad-Bhāgavatam", "Canto", "Capítulo", "Verso", "sa"),
        ("BRS", "Bhakti-rasāmṛta-sindhu", "Vibhaga", "Lahari", "Verso", "sa"),
        ("CC", "Śrī Caitanya-caritāmṛta", "Lila", "Capítulo", "Verso", "bn"),
        ("UN", "Ujjvala-nīlamaṇi", None, "Prakarana", "Verso", "sa")
    ]
    cursor.executemany("INSERT OR IGNORE INTO library_books (acronym, book_title, label_l1, label_l2, label_l3, language_default) VALUES (?,?,?,?,?,?)", livros)

if __name__ == "__main__":
    setup_database()