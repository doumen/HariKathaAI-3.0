import fitz
import sqlite3
import json
import os
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Ingest_Checkpointed")

DB_PATH = "database/harikatha.db"
PDF_PATH = "downloads/Sri_Slokamritam.pdf"

def verse_exists(conn, page_num):
    """Verifica se já processamos esta página (evita gasto de cota)."""
    cursor = conn.cursor()
    # Procuramos por qualquer conteúdo que tenha vindo desta página/referência
    cursor.execute("SELECT id FROM library_index WHERE num_2 = ?", (page_num,))
    return cursor.fetchone() is not None

def parse_page(text, page_num):
    # Usando o Flash 2.0 que é o mais rápido e estável para você agora
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"Extract verses from page {page_num} into JSON: [{{'chapter_number': int, 'verse_number': int, 'topic_name': str, 'internal_ref': str, 'sanskrit_roman': str, 'synonyms': str, 'translation': str}}]. TEXT: {text}"
    
    try:
        response = model.generate_content(prompt)
        # Limpeza básica de Markdown se houver
        json_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_text)
    except Exception as e:
        logger.error(f"❌ Erro na página {page_num}: {e}")
        return None

def save_verse(conn, v, page_num):
    cursor = conn.cursor()
    ref = v.get('internal_ref') or f"{v.get('chapter_number')}.{v.get('verse_number')}"
    canon_id = f"SLOKA {ref}"
    
    # num_2 será usado para guardar o número da página do PDF (Checkpoint)
    cursor.execute("INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_1, num_2, num_3) VALUES (9, ?, ?, ?, ?)", 
                   (canon_id, v.get('chapter_number'), page_num, v.get('verse_number')))
    
    cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canon_id,))
    idx_id = cursor.fetchone()[0]
    
    if v.get('sanskrit_roman'):
        cursor.execute("INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body) VALUES (?, 'MULA', 'sa-rom', 'Śrī Ślokāmṛtam', ?)", (idx_id, v['sanskrit_roman']))
    if v.get('translation'):
        cursor.execute("INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body) VALUES (?, 'TRANSLATION', 'en', 'Śrī Ślokāmṛtam', ?)", (idx_id, v['translation']))
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    doc = fitz.open(PDF_PATH)
    
    for i in range(30, len(doc)):
        page_num = i + 1
        
        if verse_exists(conn, page_num):
            logger.info(f"⏭️  Página {page_num} já existe no banco. Pulando...")
            continue
            
        logger.info(f"📄 Processando página {page_num}...")
        data = parse_page(doc[i].get_text(), page_num)
        
        if data:
            verses = data if isinstance(data, list) else [data]
            for v in verses:
                save_verse(conn, v, page_num)
            logger.info(f"✅ Página {page_num} salva.")
            # Espera 3 segundos entre páginas para manter o Tier 1 estável
            time.sleep(3)
        else:
            # Se falhar, esperamos mais tempo para o cooldown
            time.sleep(10)

if __name__ == "__main__":
    main()