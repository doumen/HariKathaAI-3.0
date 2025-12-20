import sqlite3
import os

DB_PATH = "database/harikatha.db"

def check_database():
    if not os.path.exists(DB_PATH):
        print("❌ Banco de dados não encontrado!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=== 📊 RELATÓRIO DO BANCO DE DADOS ===")

    # 1. Contagem de Livros
    cursor.execute("SELECT count(*) FROM library_books")
    books = cursor.fetchone()[0]
    print(f"📚 Livros cadastrados: {books}")

    # 2. Contagem de Índices (Versos/Tópicos)
    cursor.execute("SELECT count(*) FROM library_index")
    indexes = cursor.fetchone()[0]
    print(f"📍 Entradas no Índice (Versos): {indexes}")

    # 3. Contagem de Conteúdos (Textos/Traduções)
    cursor.execute("SELECT count(*) FROM library_content")
    contents = cursor.fetchone()[0]
    print(f"📝 Blocos de Texto (Sânscrito/Traduções): {contents}")

    print("\n=== 🔍 AMOSTRA DOS ÚLTIMOS 3 VERSOS INSERIDOS ===")
    
    # Pega os 3 últimos IDs inseridos
    cursor.execute("""
        SELECT i.canonical_id, c.content_type, c.text_body 
        FROM library_content c
        JOIN library_index i ON c.index_id = i.id
        ORDER BY c.id DESC 
        LIMIT 6
    """)
    
    rows = cursor.fetchall()
    for ref, tipo, texto in rows:
        # Corta o texto se for muito longo para caber na tela
        preview = (texto[:100] + '...') if len(texto) > 100 else texto
        print(f"[{ref}] ({tipo}): {preview}")

    conn.close()

if __name__ == "__main__":
    check_database()