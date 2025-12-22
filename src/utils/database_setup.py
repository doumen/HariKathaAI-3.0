#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
setup_database.py

Cria e inicializa o banco SQLite usado pelo projeto HariKatha‑3.0.
Versão: v6.5 (com refinamentos de integridade e performance).

Autor: equipe HariKatha
"""

import os
import sqlite3
import logging
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
DB_FOLDER = "database"
DB_NAME = "harikatha.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

# Configuração de logs (nível INFO)
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
    # Habilita chaves estrangeiras e otimizações de concorrência
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    cur = conn.cursor()
    logger.info("🏗️  Construindo HariKathaAI v6.5 – schema inicial...")

    # -------------------------------------------------------------------------
    # 1. Apoio e aprendizado
    # -------------------------------------------------------------------------
    cur.executescript(
        """
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
            is_active_rule INTEGER DEFAULT 1,          -- 0 = false, 1 = true
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            language_code TEXT REFERENCES languages(code)
        );
        """
    )

    # -------------------------------------------------------------------------
    # 2. Lectures (com suporte multimídia e auditoria)
    # -------------------------------------------------------------------------
    cur.execute(
        """
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

            -- Campos de produção de mídia (mantidos por media_assets)
            path_cover_image TEXT,

            -- Campos de sincronia e auditoria
            audit_status TEXT DEFAULT 'PENDING',
            sync_diff_avg REAL,
            cut_mode TEXT,
            kirtan_offset_seconds REAL DEFAULT 0.0,
            retry_count INTEGER DEFAULT 0,

            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # -------------------------------------------------------------------------
    # 3. Media assets (flexível para novos tipos)
    # -------------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS media_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL
                CHECK (asset_type IN ('AUDIO','PDF','SRT','COVER')),
            file_path TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
        );
        """
    )

    # -------------------------------------------------------------------------
    # 4. Orquestração (pipeline jobs)
    # -------------------------------------------------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL
                CHECK (job_type IN ('DOWNLOAD','OCR','TRANSCRIBE','ALIGN',
                                    'PDF_GEN','PUBLISH')),
            lecture_id INTEGER,
            status TEXT NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','RUNNING','SUCCESS','FAILED')),
            started_at DATETIME,
            finished_at DATETIME,
            error_message TEXT,
            FOREIGN KEY (lecture_id) REFERENCES lectures(id) ON DELETE CASCADE
        );
        """
    )

    # -------------------------------------------------------------------------
    # 5. Auditoria IA (Estimativa de Custo)
    # -------------------------------------------------------------------------
    cur.executescript(
        """
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
            cost_usd            REAL,
            latency_ms          REAL,
            status_code         TEXT    NOT NULL 
                CHECK (status_code IN ('SUCCESS','ERROR','RATE_LIMIT','COST_BLOCKED')),
            payload_json        TEXT,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            error_message       TEXT,
            operation_type      TEXT DEFAULT 'GENERAL',
            UNIQUE(request_hash, model_name)
        );

        CREATE INDEX IF NOT EXISTS idx_audit_op ON ai_audit_logs (operation_type);
        """
    )

    # -------------------------------------------------------------------------
    # 6. Biblioteca (taxonomia WisdomLib)
    # -------------------------------------------------------------------------
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS library_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acronym TEXT UNIQUE NOT NULL,
            book_title TEXT NOT NULL,
            label_l1 TEXT,
            label_l2 TEXT,
            label_l3 TEXT,
            language_default TEXT NOT NULL REFERENCES languages(code)
        );

        CREATE TABLE IF NOT EXISTS library_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            canonical_id TEXT UNIQUE NOT NULL,
            num_1 INTEGER,
            num_2 INTEGER,
            num_3 INTEGER,
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
        """
    )

    # -------------------------------------------------------------------------
    # 7. Tabelas de saída (factory)
    # -------------------------------------------------------------------------
    cur.executescript(
        """
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
        """
    )

    # -------------------------------------------------------------------------
    # 8. Índices de performance
    # -------------------------------------------------------------------------
    logger.info("⚡ Criando índices de performance...")
    cur.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_lectures_state
            ON lectures (current_state);
        CREATE INDEX IF NOT EXISTS idx_lectures_date
            ON lectures (lecture_date DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_status
            ON pipeline_jobs (status);
        CREATE INDEX IF NOT EXISTS idx_jobs_failed
            ON pipeline_jobs (status) WHERE status='FAILED';
        CREATE INDEX IF NOT EXISTS idx_lib_order
            ON library_index (book_id, num_1, num_2, num_3);
        CREATE INDEX IF NOT EXISTS idx_lib_canon
            ON library_index (canonical_id);
        CREATE INDEX IF NOT EXISTS idx_lecture_verses_ts
            ON lecture_verses (lecture_id, timestamp_seconds);
        """
    )

    # -------------------------------------------------------------------------
    # 9. Triggers (auditoria automática)
    # -------------------------------------------------------------------------
    logger.info("🔧 Instalando triggers de auditoria...")
    cur.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS trg_lectures_update
        AFTER UPDATE ON lectures
        BEGIN
            UPDATE lectures SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
    )

    # -------------------------------------------------------------------------
    # 10. Dados iniciais (seed)
    # -------------------------------------------------------------------------
    seed_initial_knowledge(conn)

    # -------------------------------------------------------------------------
    # Conclusão
    # -------------------------------------------------------------------------
    conn.commit()
    conn.close()
    logger.info("✅ HariKathaAI v6.5 configurado com sucesso!")


def seed_initial_knowledge(conn: sqlite3.Connection) -> None:
    """Insere dados estáticos iniciais (idiomas, regras fonéticas e livros)."""
    cur = conn.cursor()
    logger.info("🌱 Semeando conhecimento inicial...")

    # Idiomas suportados
    cur.executemany(
        """
        INSERT OR IGNORE INTO languages (code, description) VALUES (?, ?);
        """,
        [
            ("pt", "Português"),
            ("en", "English"),
            ("sa", "Sânscrito"),
            ("bn", "Bengali"),
        ],
    )

    # Regras fonéticas/editoriais
    regras = [
        (
            r"(Luta|Lota|Loota)\s*(Svitav|Svetav|feet\s*of)",
            "lotus feet of",
            "PHONETIC",
        ),
        (
            r"(om\s+)?(Vishnupada)[\s\S]{1,40}?(?=\bBhaktivedanta|\bVana|\bNarayan)",
            "om vishnupada astottara-sata Sri Srimad ",
            "EDITORIAL",
        ),
        (
            r"\b(Sri|Srila)\s*(Ramana|Romana|Vana)\s*Maharaj",
            "Bhaktivedanta Srila Vamana Gosvami Maharaja",
            "EDITORIAL",
        ),
        (
            r"(Devotion\s*(and|&)\s*service[\.,\s]*){2,}",
            "Devotional service. ",
            "EDITORIAL",
        ),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO learning_corrections
        (wrong_term, correct_term, correction_type) VALUES (?, ?, ?);
        """,
        regras,
    )

    # Livros da biblioteca
    livros = [
        ("SB", "Śrīmad-Bhāgavatam", "Canto", "Capítulo", "Verso", "sa"),
        ("BRS", "Bhakti-rasāmṛta-sindhu", "Vibhaga", "Lahari", "Verso", "sa"),
        ("CC", "Śrī Caitanya-caritāmṛta", "Lila", "Capítulo", "Verso", "bn"),
        ("UN", "Ujjvala-nīlamaṇi", None, "Prakarana", "Verso", "sa"),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO library_books
        (acronym, book_title, label_l1, label_l2, label_l3, language_default)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        livros,
    )

    logger.info("✅ Dados iniciais inseridos.")


if __name__ == "__main__":
    setup_database()
