import sqlite3
import os

DB_PATH = "database/harikatha.db"

def check_structure():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("\n--- 🕉️ ESTRUTURA GAUDIYA NO BANCO ---")
    
    # Busca todos os tipos de conteúdo para o verso 1.1.1
    cur.execute("""
        SELECT c.content_type, c.text_body 
        FROM library_content c 
        JOIN library_index i ON c.index_id = i.id 
        WHERE i.canonical_id LIKE '%1.1.1'
    """)
    
    rows = cur.fetchall()
    if not rows:
        print("❌ Nenhum dado encontrado.")
    
    for c_type, text in rows:
        preview = (text[:60] + '...') if len(text) > 60 else text
        print(f"📦 [{c_type.ljust(15)}] : {preview}")

    conn.close()

if __name__ == "__main__":
    check_structure()