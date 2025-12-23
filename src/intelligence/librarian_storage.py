import sqlite3
import logging
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

logger = logging.getLogger("LibrarianStorage")
logger.setLevel(logging.INFO)

# ... (Funções _ensure_book_id e _ensure_index_id e _upsert_root_text mantêm-se iguais) ...
def _ensure_book_id(conn, acronym):
    cur = conn.execute("SELECT id FROM library_books WHERE acronym = ?", (acronym,))
    row = cur.fetchone()
    if not row: raise ValueError(f"Livro '{acronym}' não encontrado.")
    return row[0]

def _ensure_index_id(conn, book_id, canonical_id, verse_ref):
    parts = verse_ref.split(".")
    n1 = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    n2 = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    n3 = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    conn.execute("INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_1, num_2, num_3, page_number) VALUES (?, ?, ?, ?, ?, 0)", (book_id, canonical_id, n1, n2, n3))
    cur = conn.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canonical_id,))
    return cur.fetchone()[0]

def _upsert_root_text(conn, index_id, sanskrit, translit):
    if not sanskrit and not translit: return
    conn.execute("INSERT OR REPLACE INTO library_root_text (index_id, primary_script, transliteration) VALUES (?, ?, ?)", (index_id, sanskrit, translit))
    logger.info(f"🕉️ Texto Raiz atualizado.")

# --- ATUALIZADO: Lida com a lista de traduções ---
def _upsert_translation(conn, index_id, lang, translator, text):
    if not text or len(text.strip()) < 2: return
    
    # O UNIQUE(index_id, language_code, translator) garante que
    # se rodarmos o script 2 vezes, ele atualiza, não duplica.
    conn.execute("""
        INSERT OR REPLACE INTO library_translations
        (index_id, language_code, translator, text_body)
        VALUES (?, ?, ?, ?)
    """, (index_id, lang, translator, text.strip()))
    
    logger.info(f"🌍 Tradução ({translator}) gravada.")

def save_scraped_verse(verse_data: dict, book_acronym: str) -> None:
    if not verse_data or not verse_data.get('reference'): return

    conn = sqlite3.connect(DB_PATH)
    try:
        book_id = _ensure_book_id(conn, book_acronym)
        canonical_id = f"{book_acronym}_{verse_data['reference']}"
        index_id = _ensure_index_id(conn, book_id, canonical_id, verse_data['reference'])

        # 1. Raiz
        _upsert_root_text(conn, index_id, verse_data.get("sanskrit"), verse_data.get("transliteration"))

        # 2. Traduções (Lista)
        translations = verse_data.get("english_translations", [])
        
        # Se vier como string única (compatibilidade antiga), transforma em lista
        if isinstance(translations, str):
            translations = [translations]

        if not translations:
            # Tenta pegar da chave antiga se a nova falhar
            old_key = verse_data.get("english_translation")
            if old_key: translations = [old_key]

        # Loop Inteligente
        for i, text in enumerate(translations):
            if len(translations) > 1:
                # Se tem mais de uma, usamos sufixos: WisdomLib (1), WisdomLib (2)
                translator_name = f"WisdomLib ({i+1})"
            else:
                # Se tem só uma, mantém o nome limpo
                translator_name = "WisdomLib"

            _upsert_translation(conn, index_id, "en", translator_name, text)

        conn.commit()
        logger.info(f"✅ Verso {canonical_id} salvo com {len(translations)} traduções.")
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
    finally:
        conn.close()