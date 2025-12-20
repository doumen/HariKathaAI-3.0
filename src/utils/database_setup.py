import sqlite3
import os

DB_PATH = "database/harikatha.db"

def setup_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # Ativação crucial de Chaves Estrangeiras
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    print("🚀 Configurando HariKathaAI 3.5 - Sistema Unificado...")

    # --- 1. TABELAS DE APOIO ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS languages (
        code TEXT PRIMARY KEY CHECK (length(code) BETWEEN 2 AND 3),
        description TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL
    );
    """)

    # --- 2. NÚCLEO DA BIBLIOTECA (LIBRARY) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS library_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_title TEXT NOT NULL,
        acronym TEXT UNIQUE NOT NULL,
        author_id INTEGER,
        language_default TEXT NOT NULL REFERENCES languages(code),
        total_pages INTEGER,
        last_processed_page INTEGER DEFAULT 0,
        FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS library_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        canonical_id TEXT UNIQUE NOT NULL,
        section TEXT,
        num_1 INTEGER, 
        num_2 INTEGER,
        page_number INTEGER NOT NULL,
        updated_at DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),
        FOREIGN KEY (book_id) REFERENCES library_books (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS library_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_id INTEGER NOT NULL,
        content_type TEXT CHECK(content_type IN ('MULA','TIKA','TRANSLATION','SYNONYMS','EXEGESIS')),
        author_id INTEGER NOT NULL,
        language_code TEXT NOT NULL REFERENCES languages(code),
        text_body TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        updated_at DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),
        FOREIGN KEY (index_id) REFERENCES library_index (id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES authors(id)
    );
    """)

    # --- 3. NÚCLEO DE AULAS E PIPELINE ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_hash TEXT UNIQUE,
        lecture_title TEXT NOT NULL,
        lecture_date DATETIME NOT NULL,
        current_state TEXT DEFAULT 'RAW' CHECK (current_state IN ('RAW', 'SIEVED', 'TRANSCRIBED', 'FACTORY_READY', 'PUBLISHED')),
        audio_path TEXT,
        transcript_json TEXT,
        metadata_json TEXT,
        updated_at DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),
        UNIQUE(lecture_title, lecture_date)
    );
    """)

    # --- 4. PONTE DINÂMICA (AULA -> VERSO) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lecture_verses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER NOT NULL,
        library_index_id INTEGER NOT NULL,
        timestamp_seconds INTEGER NOT NULL, 
        context_note TEXT, -- Insight específico do Maharaja nesta aula
        is_implicit BOOLEAN DEFAULT 0, -- 1 se identificado por IA sem citação direta
        created_at DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),
        FOREIGN KEY (lecture_id) REFERENCES lectures (id) ON DELETE CASCADE,
        FOREIGN KEY (library_index_id) REFERENCES library_index (id) ON DELETE CASCADE,
        UNIQUE(lecture_id, library_index_id, timestamp_seconds)
    );
    """)

    # --- 5. AUDITORIA E BLINDAGEM DE CUSTO ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        page_number INTEGER NOT NULL,
        status TEXT CHECK (status IN ('SUCCESS','FAILED','RETRY')) NOT NULL,
        tokens_used INTEGER,
        processed_at DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),
        UNIQUE(book_id, page_number),
        FOREIGN KEY (book_id) REFERENCES library_books(id) ON DELETE CASCADE
    );
    """)

    # --- 6. ÍNDICES DE PERFORMANCE ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lib_order ON library_index (book_id, num_1, num_2);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lecture_verses_time ON lecture_verses (lecture_id, timestamp_seconds);")

    # Inserção de Idiomas
    cursor.executemany("INSERT OR IGNORE INTO languages (code, description) VALUES (?, ?)", 
                       [('pt', 'Português'), ('en', 'English'), ('sa', 'Sânscrito'), ('bn', 'Bengali'), ('hi', 'Hindi')])

    conn.commit()
    conn.close()
    print("✅ HariKathaAI 3.5 configurado com sucesso! Pronto para ingestão.")

if __name__ == "__main__":
    setup_database()