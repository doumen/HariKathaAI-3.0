#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
librarian_storage.py (V8.0 - Suporte a Word-for-Word)
"""

import os
import sqlite3
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

logger = logging.getLogger("LibrarianStorage")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)

def _get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)

def _ensure_book_id(conn: sqlite3.Connection, acronym: str) -> int:
    cur = conn.execute("SELECT id FROM library_books WHERE acronym = ?", (acronym,))
    row = cur.fetchone()
    if not row: raise ValueError(f"Livro '{acronym}' não encontrado!")
    return row[0]

def _ensure_index_id(conn: sqlite3.Connection, book_id: int, canonical_id: str, verse_ref: str) -> int:
    parts = verse_ref.split(".")
    n1 = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    n2 = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    n3 = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

    conn.execute("INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_1, num_2, num_3) VALUES (?, ?, ?, ?, ?)", (book_id, canonical_id, n1, n2, n3))
    return conn.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canonical_id,)).fetchone()[0]

def _upsert_root_text(conn: sqlite3.Connection, index_id: int, sanskrit: str, translit: str) -> None:
    if not sanskrit and not translit: return
    conn.execute("INSERT OR REPLACE INTO library_root_text (index_id, primary_script, transliteration) VALUES (?, ?, ?)", (index_id, sanskrit, translit))

def _upsert_translation(
    conn: sqlite3.Connection, 
    index_id: int, 
    lang: str, 
    translator: str, 
    text_body: str, 
    word_for_word: str = None, # <--- NOVO ARGUMENTO
    source_ref: str = None, 
    commentary: str = None
) -> None:
    """
    Salva tradução completa, incluindo word_for_word em coluna separada.
    """
    body = text_body.strip() if text_body else ""
    w2w = word_for_word.strip() if word_for_word else None
    ref = source_ref.strip() if source_ref else None
    comm = commentary.strip() if commentary else None

    # Se tudo vazio, sai
    if not body and not w2w and not ref and not comm: return

    conn.execute("""
        INSERT OR REPLACE INTO library_translations
        (index_id, language_code, translator, text_body, word_for_word, source_ref, commentary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (index_id, lang, translator, body, w2w, ref, comm))

def _upsert_commentary(conn: sqlite3.Connection, index_id: int, lang: str, commentator: str, text: str) -> None:
    if not text or len(text.strip()) < 5: return
    conn.execute("INSERT OR REPLACE INTO library_commentaries (index_id, language_code, commentator, text_body) VALUES (?, ?, ?, ?)", (index_id, lang, commentator, text.strip()))