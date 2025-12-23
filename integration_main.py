import subprocess
import json
import logging
import os
# Importamos a função de salvamento do seu arquivo oficial
from src.intelligence.librarian_storage import save_scraped_verse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IntegrationMain")

def capture_and_save(book_acronym, verse_ref):
    book_map = {
        "BRS": "Bhakti-rasamrta-sindhu",
        "SB": "Srimad-Bhagavatam",
        "CC": "Caitanya-caritamrta"
    }

    full_book_name = book_map.get(book_acronym, book_acronym)
    logger.info(f"🚀 Iniciando captura: {full_book_name} {verse_ref}")

    # 1. Executa o Scraper
    result = subprocess.run(
        ['node', 'tests/test_wisdom_fetcher.js', full_book_name, verse_ref],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    # 2. Lógica de Sucesso: O returncode deve ser 0
    if result.returncode == 0:
        # Mostramos os logs do Node apenas como informação, não como erro
        if result.stderr:
            print(f"--- Logs do Scraper ---\n{result.stderr}\n-----------------------")

        try:
            # 3. Busca o JSON na saída (stdout)
            raw_output = result.stdout.strip()
            start_index = raw_output.find('{')
            end_index = raw_output.rfind('}') + 1

            if start_index != -1 and end_index > start_index:
                verse_data = json.loads(raw_output[start_index:end_index])
                
                # 4. Tenta salvar no banco
                save_scraped_verse(verse_data, book_acronym=book_acronym)
                logger.info(f"✅ Verso {verse_ref} processado com sucesso!")
            else:
                logger.error("❌ O Scraper rodou, mas não entregou um JSON válido no stdout.")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar o JSON: {e}")
            logger.debug(f"Saída bruta: {result.stdout}")
    else:
        # Aqui sim é um erro real de execução do Node
        logger.error(f"❌ Erro Fatal no Node.js (Exit Code {result.returncode}):")
        logger.error(result.stderr)

if __name__ == "__main__":
    # Teste com o verso 1.1.1
    capture_and_save("BRS", "1.1.1")