import sqlite3

def setup_giti_book():
    conn = sqlite3.connect("database/harikatha.db")
    cursor = conn.cursor()
    
    # Inserindo o Giti-guccha na tabela de livros
    cursor.execute('''
        INSERT OR IGNORE INTO library_books (id, title, acronym, author, language_default)
        VALUES (10, 'Gaudīya-Gīti-guccha', 'GITI', 'Various Acaryas', 'bn')
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Livro 'GITI' registrado com sucesso no ID 10.")

if __name__ == "__main__":
    setup_giti_book()