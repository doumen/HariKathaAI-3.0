import sqlite3
import os
import sys

# Ajuste de path para rodar da pasta src/factory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

DB_PATH = os.path.join(project_root, "database", "harikatha.db")

def format_verse_card(book_acronym, verse_ref):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    canonical_id = f"{book_acronym}_{verse_ref}"
    
    # 1. Busca Sânscrito e Transliteração (Tabela Raiz)
    sql_root = """
        SELECT r.primary_script, r.transliteration
        FROM library_root_text r
        JOIN library_index i ON r.index_id = i.id
        WHERE i.canonical_id = ?
    """
    root = cur.execute(sql_root, (canonical_id,)).fetchone()
    
    if not root:
        print(f"❌ Verso {canonical_id} não encontrado no banco.")
        return

    # 2. Busca a Tradução Gaudiya (Tabela Traduções)
    sql_trans = """
        SELECT t.text_body
        FROM library_translations t
        JOIN library_index i ON t.index_id = i.id
        WHERE i.canonical_id = ? 
          AND t.translator = 'AI_Gaudiya_PT'
    """
    translation = cur.execute(sql_trans, (canonical_id,)).fetchone()
    
    conn.close()

    # --- MONTAGEM DO CARD ---
    sanskrit = root[0]
    translit = root[1]
    pt_text = translation[0] if translation else "[Tradução pendente... rode o scholar.py]"

    print("\n" + "="*50)
    print(f"🌺 {book_acronym} {verse_ref} 🌺")
    print("="*50)
    print(f"\n🕉️  TEXTO ORIGINAL:\n{sanskrit}")
    print(f"\n🔤 TRANSLITERAÇÃO:\n{translit}")
    print("-" * 50)
    print(f"🇧🇷 TRADUÇÃO (Gaudiya):\n{pt_text}")
    print("="*50 + "\n")

if __name__ == "__main__":
    # Teste com um verso que sabemos que existe
    format_verse_card("BRS", "1.1.1")