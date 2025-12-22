import subprocess
import json
import sqlite3
from src.intelligence.librarian_storage import save_scraped_verse # A função que criamos

def capture_and_save(book, verse):
    print(f"🚀 Iniciando captura de {book} {verse}...")

    # 1. Chama o Node.js para buscar o dado
    result = subprocess.run(
        ['node', 'tests/test_wisdom_fetcher.js', book, verse],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    if result.returncode == 0:
        try:
            # 2. Extrai o JSON da saída do Node
            raw_output = result.stdout.strip()
            start_index = raw_output.find('{')
            end_index = raw_output.rfind('}') + 1
            
            if start_index != -1:
                data = json.loads(raw_output[start_index:end_index])
                
                # 3. Salva no Banco v6.5
                # O 'BRS' deve bater com o ACRONYM que está no seu setup_database.py
                save_scraped_verse(data, book_acronym="BRS")
            else:
                print("❌ Nenhum JSON encontrado na resposta do Node.")
        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
    else:
        print(f"❌ Erro no Scraper: {result.stderr}")

if __name__ == "__main__":
    # Comando para inserir o verso específico
    capture_and_save("Bhakti-rasamrta-sindhu", "1.1.1")