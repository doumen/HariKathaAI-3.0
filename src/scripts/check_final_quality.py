import sqlite3

# Ajuste o caminho se necessário
conn = sqlite3.connect("database/harikatha.db")
cursor = conn.cursor()

# Vamos pegar os casos que eram problemáticos
ids_to_check = ['SLK_0.1', 'SLK_1.18', 'SLK_6.65']

print(f"{'ID':<10} | {'TIPO':<10} | {'CONTEÚDO (Amostra)'}")
print("-" * 80)

for canon_id in ids_to_check:
    # Busca Raiz
    cursor.execute("""
        SELECT r.transliteration 
        FROM library_root_text r 
        JOIN library_index i ON r.index_id = i.id 
        WHERE i.canonical_id = ?
    """, (canon_id,))
    root = cursor.fetchone()
    root_txt = root[0][:40].replace('\n', ' ') + "..." if root else "❌ (Vazio)"
    print(f"{canon_id:<10} | {'Root':<10} | {root_txt}")

    # Busca W2W e Tradução
    cursor.execute("""
        SELECT t.word_for_word, t.text_body 
        FROM library_translations t 
        JOIN library_index i ON t.index_id = i.id 
        WHERE i.canonical_id = ?
    """, (canon_id,))
    res = cursor.fetchone()
    
    if res:
        w2w, body = res
        w2w_txt = w2w[:40].replace('\n', ' ') + "..." if w2w else "--- (Sem W2W)"
        body_txt = body[:40].replace('\n', ' ') + "..." if body else "❌ (Vazio)"
        
        print(f"{'':<10} | {'W2W':<10} | {w2w_txt}")
        print(f"{'':<10} | {'Body':<10} | {body_txt}")
    else:
        print(f"{'':<10} | {'Trans':<10} | ❌ (Não encontrada)")
    
    print("-" * 80)

conn.close()