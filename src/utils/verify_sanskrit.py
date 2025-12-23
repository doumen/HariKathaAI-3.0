import sqlite3
import os

# Caminho absoluto para evitar erro de "banco não encontrado"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def check_sanskrit():
    print(f"📂 Conectando em: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ Arquivo do banco de dados não encontrado!")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("SELECT text_body FROM library_content WHERE content_type='SANSKRIT'")
        row = cur.fetchone()
        
        print("\n--- 🕉️ RESULTADO DO BANCO ---")
        if row:
            print(row[0])
            print("-----------------------------")
            
            # Validação rápida
            if "Resources" in row[0] or "English translation" in row[0]:
                print("⚠️  AVISO: O texto ainda contém 'lixo' (cabeçalhos/tradução).")
            else:
                print("✅ SUCESSO: O texto está limpo (apenas Sânscrito)!")
        else:
            print("❌ Nenhum conteúdo do tipo 'SANSKRIT' encontrado.")
            
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_sanskrit()