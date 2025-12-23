import sqlite3
import os

# --- 1. Garante que pegamos o caminho ABSOLUTO do banco correto ---
current_dir = os.path.dirname(os.path.abspath(__file__))
# Sobe dois níveis para chegar na raiz do projeto
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
db_path = os.path.join(project_root, "database", "harikatha.db")

print(f"📂 Alvo do Banco de Dados: {db_path}")

if not os.path.exists(db_path):
    print("❌ ERRO: O arquivo harikatha.db não existe neste caminho!")
    print(f"   Verifique se a pasta 'database' está na raiz: {project_root}")
    exit()

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# --- 2. Verifica se o livro existe ---
print("\n🔍 Buscando livro 'SLK'...")
cur.execute("SELECT id, book_title FROM library_books WHERE acronym = 'SLK'")
book = cur.fetchone()

if not book:
    print("❌ O livro 'SLK' NÃO foi encontrado na tabela library_books.")
    print("   Livros disponíveis no banco:")
    for row in cur.execute("SELECT id, acronym FROM library_books"):
        print(f"   ID {row[0]}: {row[1]}")
    conn.close()
    exit()

book_id = book[0]
print(f"✅ Livro Encontrado: ID {book_id} - '{book[1]}'")

# --- 3. Conta os dados antes de apagar ---
count_idx = cur.execute("SELECT COUNT(*) FROM library_index WHERE book_id=?", (book_id,)).fetchone()[0]
print(f"📊 Registros atuais vinculados ao SLK: {count_idx}")

if count_idx == 0:
    print("⚠️  O banco já está limpo para este livro. Nada a fazer.")
else:
    # --- 4. Executa a Limpeza em Cascata ---
    print("\n🗑️  Iniciando deleção...")
    
    # Apaga Tags (Se houver)
    cur.execute("DELETE FROM content_tags WHERE library_index_id IN (SELECT id FROM library_index WHERE book_id=?)", (book_id,))
    print(f"   - Tags removidas: {cur.rowcount}")

    # Apaga Texto Raiz
    cur.execute("DELETE FROM library_root_text WHERE index_id IN (SELECT id FROM library_index WHERE book_id=?)", (book_id,))
    print(f"   - Textos Raiz removidos: {cur.rowcount}")

    # Apaga Traduções
    cur.execute("DELETE FROM library_translations WHERE index_id IN (SELECT id FROM library_index WHERE book_id=?)", (book_id,))
    print(f"   - Traduções removidas: {cur.rowcount}")

    # Apaga Comentários
    cur.execute("DELETE FROM library_commentaries WHERE index_id IN (SELECT id FROM library_index WHERE book_id=?)", (book_id,))
    print(f"   - Comentários removidos: {cur.rowcount}")

    # Finalmente, apaga o Índice
    cur.execute("DELETE FROM library_index WHERE book_id=?", (book_id,))
    print(f"   - Índices removidos: {cur.rowcount}")

    cur.execute("ALTER TABLE library_translations ADD COLUMN source_ref TEXT;")
    cur.execute("ALTER TABLE library_translations ADD COLUMN commentary TEXT;")
    
    conn.commit()
    print("\n✨ Limpeza concluída e salva (COMMIT)!")

conn.close()