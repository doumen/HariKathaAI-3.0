import sqlite3
import os
import logging
from typing import Optional
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
DB_FOLDER = "database"
DB_NAME = "harikatha.db"
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DB_Builder")

def create_connection() -> Optional[sqlite3.Connection]:
    """Cria conexão com o banco SQLite e garante que a pasta existe."""
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    try:
        conn = sqlite3.connect(DB_PATH)
        # Habilita suporte a chaves estrangeiras para integridade relacional
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        return None

def create_indexes(conn: sqlite3.Connection):
    """Cria índices estratégicos para performance."""
    cursor = conn.cursor()
    
    # 1. Índices Simples (Buscas diretas)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_state ON lectures (current_state)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_url ON lectures (youtube_url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_hash ON lectures (file_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_corrections_wrong ON learning_corrections (wrong_term)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lib_index_canon ON library_index (canonical_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lib_content_ref ON library_content (index_id)")
    
    # 2. Índices Compostos (Consultas complexas frequentes)
    # Para: "Pegue as últimas aulas publicadas"
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lectures_state_date ON lectures (current_state, date_recorded)")
    # Para: "Liste todos os versos desta aula na ordem que apareceram"
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lecture_verses_ts ON lecture_verses (lecture_id, timestamp_seconds)")
    # Para: "Pegue as regras ativas ordenadas por confiança (prioridade)"
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_corrections_active ON learning_corrections (is_active_rule, confidence_score)")
    # Para: "Pegue a tradução em PT deste verso específico"
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lib_content_type_lang ON library_content (content_type, language_code)")
    
    conn.commit()
    logger.info("⚡ Índices de performance criados/verificados.")

def create_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()
    logger.info("🏗️  Construindo esquema do Banco de Dados...")

    # 1. LECTURES (Com Constraints de Validação e Máquina de Estados)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        youtube_url TEXT UNIQUE NOT NULL,
        youtube_id TEXT,
        file_hash TEXT UNIQUE,
        title_original TEXT,
        date_recorded DATE,
        
        -- Validação de sanidade
        duration_seconds REAL CHECK (duration_seconds IS NULL OR duration_seconds > 0),
        language_detected TEXT DEFAULT 'en',

        -- Máquina de Estados Rígida
        current_state TEXT DEFAULT 'NEW' CHECK (current_state IN ('NEW', 'HARVESTED', 'PREPROCESSED', 'TRANSCRIBED', 'AUDITED', 'SEMANTIC_OK', 'PUBLISHED', 'FAILED', 'ARCHIVED')),
        
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        error_log TEXT,
        
        -- Limite de retries para evitar loops infinitos
        retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0 AND retry_count <= 5),
        
        cut_mode TEXT,
        kirtan_offset_seconds REAL DEFAULT 0.0,
        audit_status TEXT DEFAULT 'PENDING',
        sync_diff_avg REAL,
        
        path_audio_master TEXT,
        path_pdf_fascicle TEXT,
        path_srt_zip TEXT,
        path_cover_image TEXT
    )
    ''')

    # 2. CORRECTIONS (Dicionário Vivo)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS learning_corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wrong_term TEXT NOT NULL,
        correct_term TEXT NOT NULL,
        correction_type TEXT DEFAULT 'PHONETIC',
        frequency INTEGER DEFAULT 1,
        confidence_score REAL DEFAULT 0.5,
        is_active_rule BOOLEAN DEFAULT 1 CHECK (is_active_rule IN (0, 1)),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 3. LIBRARY BOOKS (Catálogo WisdomLib)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS library_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acronym TEXT UNIQUE NOT NULL,
        title_canonical TEXT,
        label_level_1 TEXT, -- Ex: Canto / Vibhaga / Parte
        label_level_2 TEXT, -- Ex: Capítulo / Lahari / Tópico
        label_level_3 TEXT  -- Ex: Verso
    )
    ''')

    # 4. LIBRARY INDEX (GPS Universal)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS library_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        canonical_id TEXT UNIQUE NOT NULL, -- Ex: "SB 1.1.1" ou "SLOKA Guru-tattva"
        num_1 INTEGER DEFAULT 0,
        num_2 INTEGER DEFAULT 0,
        num_3 INTEGER DEFAULT 0,
        num_4 INTEGER DEFAULT 0,
        FOREIGN KEY (book_id) REFERENCES library_books (id)
    )
    ''')

    # 5. LIBRARY CONTENT (Conteúdo Multilíngue)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS library_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_id INTEGER,
        content_type TEXT,  -- MULA, TRANSLATION, PURPORT, SYNONYMS
        language_code TEXT, -- sa-dev, sa-rom, bn, pt, en
        author_source TEXT, -- Vyasa, BBT, Gemini_Vision
        text_body TEXT,
        FOREIGN KEY (index_id) REFERENCES library_index (id)
    )
    ''')

    # 6. LECTURE VERSES (Relacionamento Aula-Verso)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lecture_verses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER,
        library_index_id INTEGER,
        timestamp_seconds REAL,
        confidence_score REAL,
        FOREIGN KEY (lecture_id) REFERENCES lectures (id),
        FOREIGN KEY (library_index_id) REFERENCES library_index (id)
    )
    ''')

    # 7. CHAPTERS SOURCE (Matéria-prima para Livros)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chapters_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER,
        title_chapter TEXT,
        content_markdown TEXT, 
        tags_json TEXT,
        FOREIGN KEY (lecture_id) REFERENCES lectures (id)
    )
    ''')

    # 8. BLOG POSTS (Publicação Web)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blog_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER,
        title_seo TEXT,
        slug TEXT UNIQUE,
        excerpt TEXT,
        content_html TEXT,
        publish_status TEXT DEFAULT 'DRAFT',
        FOREIGN KEY (lecture_id) REFERENCES lectures (id)
    )
    ''')
    
    # 9. VIRAL SEGMENTS (Shorts/Reels)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS viral_segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lecture_id INTEGER,
        start_time REAL,
        end_time REAL,
        topic TEXT,
        viral_score INTEGER,
        path_video_output TEXT,
        FOREIGN KEY (lecture_id) REFERENCES lectures (id)
    )
    ''')

    conn.commit()

def seed_initial_knowledge(conn: sqlite3.Connection):
    """Popula o banco com transação atômica (Rollback em caso de falha)."""
    cursor = conn.cursor()
    logger.info("🌱 Semeando conhecimento inicial...")

    try:
        with conn: # Context Manager garante transação e rollback
            count_rules = 0
            count_books = 0

            # --- 1. CORREÇÕES (Regras Blindadas com Lookahead) ---
            regras = [
                # A. O MANTRA DOS PÉS DE LÓTUS (Groq: "Luta Svitav")
                (r"(Luta|Lota|Loota)\s*(Svitav|Svetav|sweet\s*of|feet\s*of|feat\s*of)", 
                 "lotus feet of", "PHONETIC"),

                # B. DANDAVATS (Groq: "Dandavada")
                (r"\b(Dandavada|Danvath|Dandavat)\s*(Pranam|Pranama)?", 
                 "dandavat-pranama", "PHONETIC"),

                # C. PADRONIZAÇÃO DO INÍCIO (Nitya-lila ... Vishnupada)
                # Corrige qualquer variação estranha até chegar na palavra chave "Vishnupada"
                (r"(Nityalabh|Nityalela|Nitya\s*lila)[\s\S]{1,50}?(Vishnu\s*pada|Vishnupada|Vishnu\s*pod)", 
                 "nitya-lila pravista om vishnupada", "PHONETIC"),

                # D. A "PONTE" DOS TÍTULOS (A Regra Blindada com Lookahead)
                # Encontra "Vishnupada" e come tudo até encontrar o Nome do Guru.
                # O (?=...) é o Lookahead: ele para ANTES de tocar no nome.
                (r"(om\s+)?(Vishnu\s*pada|Vishnupada|Vishnu\s*pod)[\s\S]{1,40}?(?=\bBhaktivedanta|\bVana|\bNarayan|\bGovinda|\bSridhar|\bSwami)", 
                 "om vishnupada astottara-sata Sri Srimad ", "EDITORIAL"),

                # E. IDENTIFICAÇÃO E CORREÇÃO DE NOMES ESPECÍFICOS
                # Se o Groq ouviu "Sri Ramana" ou "Romana", forçamos "Srila Vamana"
                (r"\b(Sri|Srila)\s*(Ramana|Romana|Vana)\s*(Vishnu|Goswami)?\s*Maharaj", 
                 "Bhaktivedanta Srila Vamana Gosvami Maharaja", "EDITORIAL"),
                 
                # Garante Narayana Maharaja completo
                (r"Bhaktivedanta\s*(Srila)?\s*Narayan\s*(Goswami)?\s*Maharaj", 
                 "Bhaktivedanta Srila Narayana Gosvami Maharaja", "EDITORIAL"),

                # F. CORREÇÃO DE LOOPS DO WHISPER
                # Se "Devotion and service" aparecer 2 ou mais vezes seguidas
                (r"(Devotion\s*(and|&)\s*service[\.,\s]*){2,}", 
                 "Devotional service. ", "EDITORIAL"),
                 
                # G. DEFINIÇÕES SÂNSCRITAS (Sutras)
                (r"\b(bhajyate|bhajate|bajate)\s*(sevvate|sevate|savate)\s*(iti|ity)\s*(bhakti|bhaktiḥ)", 
                 "bhajate sevate iti bhaktiḥ", "PHONETIC"),
                 
                (r"\b(Seva|Siva)\s*(vritti|vriti|britti|briti)", 
                 "seva-vritti", "PHONETIC"),

                # H. A TRANSIÇÃO "SIMULTANEOUSLY"
                (r"\b(17th|Seventh|And\s*seventh)\s*(Ashtolikas|Ashtoli|naturally)", 
                 "and simultaneously I offer my humble, respectful obeisances at the", "EDITORIAL"),

                # I. LIMPEZA GERAL
                (r"\b(Obleisenses|Obeisance)\b", "obeisances", "PHONETIC"),
                (r"\b(presented|present)\s+all\s+of\s+my\s+respectful\s+guest", 
                 "and all my respectful guests present here", "EDITORIAL"),
                 
                # Correção do "Bia" -> Bhakti
                (r"\b(bia|bi)\s+(tattva|yoga|means|service|cult)", "bhakti", "PHONETIC"),
            ]
            
            for wrong, right, type_ in regras:
                cursor.execute("SELECT id FROM learning_corrections WHERE wrong_term = ?", (wrong,))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO learning_corrections (wrong_term, correct_term, correction_type, frequency, is_active_rule, confidence_score)
                        VALUES (?, ?, ?, 100, 1, 1.0)
                    ''', (wrong, right, type_))
                    count_rules += 1

            # --- 2. LIVROS (WisdomLib Structure) ---
            livros = [
                # Escrituras Primárias
                ("SB", "Śrīmad-Bhāgavatam", "Canto", "Capítulo", "Verso"),
                ("BG", "Bhagavad-gītā", None, "Capítulo", "Verso"),
                ("CC", "Śrī Caitanya-caritāmṛta", "Lila", "Capítulo", "Verso"),
                ("BRS", "Bhakti-rasāmṛta-sindhu", "Vibhaga", "Lahari", "Verso"),
                ("GG", "Śrī Gīta-govinda", "Sarga", "Prabandha", "Verso"),
                ("HBV", "Śrī Hari-bhakti-vilāsa", "Vilasa", None, "Verso"),
                ("UN", "Ujjvala-nīlamaṇi", None, "Prakarana", "Verso"),
                
                # Livros de Referência (Antologias)
                ("SLOKA", "Śrī Ślokāmṛtam", "Parte", "Tópico", "Verso"), 
                ("VMS", "Śrī Vaiṣṇava Manjūṣā", "Tattva", None, "Verso")
            ]
            
            for acr, title, l1, l2, l3 in livros:
                cursor.execute('''
                    INSERT OR IGNORE INTO library_books (acronym, title_canonical, label_level_1, label_level_2, label_level_3)
                    VALUES (?, ?, ?, ?, ?)
                ''', (acr, title, l1, l2, l3))
                count_books += 1

            # --- 3. TESTE DE UNIDADE: BRS 1.1.11 ---
            cursor.execute("SELECT id FROM library_books WHERE acronym='BRS'")
            res = cursor.fetchone()
            if res:
                brs_id = res[0]
                
                # Tenta Inserir Verso de Teste
                cursor.execute("INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_1, num_2, num_3) VALUES (?, 'BRS 1.1.11', 1, 1, 11)", (brs_id,))
                
                # Lógica de recuperação de ID robusta
                if cursor.rowcount > 0:
                    idx_id = cursor.lastrowid
                else:
                    cursor.execute("SELECT id FROM library_index WHERE canonical_id='BRS 1.1.11'")
                    result = cursor.fetchone()
                    idx_id = result[0] if result else None
                
                if idx_id:
                    cursor.execute("INSERT OR IGNORE INTO library_content (index_id, content_type, language_code, author_source, text_body) VALUES (?, 'MULA', 'sa-dev', 'Rupa_Goswami', ?)", (idx_id, "अन्याभिलाषिता-शून्यं..."))

            logger.info(f"✅ Seed inicial concluído: {count_rules} regras e {count_books} livros processados.")

    except Exception as e:
        logger.error(f"❌ Erro crítico no Seed (Transação cancelada): {e}")
        raise # Relança o erro

def main():
    conn = create_connection()
    if conn:
        create_tables(conn)
        create_indexes(conn)
        seed_initial_knowledge(conn)
        conn.close()
        logger.info("🚀 Banco de Dados 'harikatha.db' (V5.0 Enterprise) pronto!")

if __name__ == "__main__":
    main()