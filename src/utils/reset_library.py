import sqlite3

def reset_library():
    conn = sqlite3.connect("database/harikatha.db")
    cursor = conn.cursor()
    print("🧹 Limpando tabelas da biblioteca...")
    
    # Limpa as tabelas na ordem correta devido às chaves estrangeiras
    cursor.execute("DELETE FROM library_content")
    cursor.execute("DELETE FROM library_index")
    # Opcional: Reiniciar o contador de IDs
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('library_content', 'library_index')")
    
    conn.commit()
    conn.close()
    print("✅ Biblioteca resetada. Pronto para nova ingestão.")

if __name__ == "__main__":
    reset_library()