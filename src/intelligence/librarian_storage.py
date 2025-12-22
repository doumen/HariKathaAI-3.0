import sqlite3
import json
import logging

def save_scraped_verse(data, book_acronym="BRS"):
    """
    Salva os dados do scraper nas tabelas library_index e library_content.
    """
    DB_PATH = "database/harikatha.db"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # 1. Buscar o ID do livro pelo Acrônimo (ex: BRS)
        cur.execute("SELECT id FROM library_books WHERE acronym = ?", (book_acronym,))
        book_row = cur.fetchone()
        if not book_row:
            print(f"❌ Livro {book_acronym} não encontrado no banco. Rode o setup_database primeiro.")
            return
        book_id = book_row[0]

        # 2. Criar o Índice (library_index)
        # O canonical_id evita duplicatas (ex: BRS_1.1.1)
        canonical_id = f"{book_acronym}_{data['referencia'].replace(' ', '_')}"
        
        cur.execute("""
            INSERT OR IGNORE INTO library_index (book_id, canonical_id, page_number)
            VALUES (?, ?, ?)
        """, (book_id, canonical_id, 0))
        
        # Recuperar o index_id (seja o novo ou o existente)
        cur.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canonical_id,))
        index_id = cur.fetchone()[0]

        # 3. Salvar o Conteúdo (library_content) - Versão Original (sa)
        # Usamos INSERT OR REPLACE para atualizar caso o verso já exista
        cur.execute("""
            INSERT OR REPLACE INTO library_content (index_id, content_type, language_code, text_body)
            VALUES (?, ?, ?, ?)
        """, (index_id, 'ORIGINAL', 'sa', data['sânscrito']))

        # 4. Salvar a Transliteração (como uma versão alternativa)
        if data.get('transliteracao'):
            cur.execute("""
                INSERT OR REPLACE INTO library_content (index_id, content_type, language_code, text_body)
                VALUES (?, ?, ?, ?)
            """, (index_id, 'TRANSLITERATION', 'en', data['transliteracao']))

        conn.commit()
        print(f"✨ Verso {data['referencia']} eternizado no banco de dados!")

    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")
    finally:
        conn.close()