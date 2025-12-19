import fitz  # PyMuPDF
import sqlite3
import json
import os
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIGURAÇÃO ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Ingest_Sloka")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_PATH = "database/harikatha.db"
PDF_PATH = "downloads/Sri Slokamrtam Cinmaya v1.0.qxp - Sri_Slokamritam.pdf"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def clean_json_response(text):
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1: return text[start:end]
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1: return text[start:end]
        return text
    except:
        return text

def get_working_model():
    """Tenta identificar qual modelo está disponível."""
    # Lista de prioridade
    candidates = ['gemini-2.0-flash', 'gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-2.5-flash']
    return genai.GenerativeModel(candidates[0]) # Por enquanto tenta o primeiro, o erro será tratado no loop

def parse_page_with_gemini(page_text, page_num):
    # Tenta instanciar o modelo (se falhar o nome, tentamos outro no futuro, 
    # mas aqui vamos forçar o flash ou pro)
    model = genai.GenerativeModel('gemini-2.0-flash') 
    
    prompt = f"""
    You are a Vaishnava Data Archivist. Analyze this raw text from page {page_num} of 'Sri Slokamrtam'.
    Extract verses into a JSON list.
    
    JSON STRUCTURE:
    [{{
      "chapter_number": int,
      "verse_number": int,
      "topic_name": "string",
      "internal_ref": "string",
      "sanskrit_roman": "string",
      "synonyms": "string",
      "translation": "string"
    }}]

    RAW TEXT:
    {page_text}
    """
    
    response = None
    # Loop de tentativas com tratamento de erro robusto
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            break # Sucesso, sai do loop
        except Exception as e:
            logger.warning(f"⚠️ Tentativa {attempt+1} falhou na pág {page_num}: {e}")
            time.sleep(2) # Espera um pouco antes de tentar de novo
            
            # Se for erro 404 de modelo, tenta mudar para o gemini-pro na próxima
            if "404" in str(e) or "Not Found" in str(e):
                logger.info("🔄 Trocando para modelo 'gemini-pro' como fallback...")
                model = genai.GenerativeModel('gemini-pro')

    # Se saiu do loop e response continua None, desistimos desta página
    if not response:
        logger.error(f"❌ Falha total na página {page_num}. Pulando.")
        return []

    try:
        json_str = clean_json_response(response.text)
        data = json.loads(json_str)
        if isinstance(data, dict): return [data]
        return data
    except Exception as e:
        logger.error(f"⚠️ Erro ao decodificar JSON da pág {page_num}: {e}")
        return []

def save_verse_to_db(conn, verse_data):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM library_books WHERE acronym = 'SLOKA'")
    res = cursor.fetchone()
    if not res: return
    book_id = res[0]

    try:
        chap = verse_data.get('chapter_number', 0)
        v_num = verse_data.get('verse_number', 0)
        topic = verse_data.get('topic_name', 'General')
        internal_ref = verse_data.get('internal_ref')
        
        if internal_ref: canonical_id = f"SLOKA {internal_ref}"
        else: canonical_id = f"SLOKA {chap}.{v_num}"
            
        logger.info(f"   💾 Processando: {canonical_id} ({topic})...")

        cursor.execute('INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_1, num_3) VALUES (?, ?, ?, ?)', 
                       (book_id, canonical_id, chap, v_num))
        
        cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canonical_id,))
        index_id = cursor.fetchone()[0]
        
        # Inserções de conteúdo
        if verse_data.get('sanskrit_roman'):
            cursor.execute("INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body) VALUES (?, 'MULA', 'sa-rom', 'Śrī Ślokāmṛtam', ?)", (index_id, verse_data['sanskrit_roman']))

        if verse_data.get('translation'):
            cursor.execute("INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body) VALUES (?, 'TRANSLATION', 'en', 'Śrī Ślokāmṛtam', ?)", (index_id, verse_data['translation']))

        conn.commit()
        
    except sqlite3.Error as e:
        logger.error(f"❌ Erro SQL: {e}")

def main():
    if not os.path.exists(PDF_PATH):
        logger.error(f"Arquivo não encontrado: {PDF_PATH}")
        return

    conn = get_db_connection()
    doc = fitz.open(PDF_PATH)
    
    logger.info(f"📘 Iniciando ingestão... (Total: {len(doc)} págs)")
    
    # Começando da página 30 onde tem conteúdo real
    for i in range(30, len(doc)):
        page_num = i + 1
        logger.info(f"📄 Lendo página {page_num}...")
        
        text = doc[i].get_text()
        if len(text) < 50: continue

        verses = parse_page_with_gemini(text, page_num)
        
        if verses:
            logger.info(f"   ✅ Encontrado(s) {len(verses)} verso(s).")
            for v in verses:
                save_verse_to_db(conn, v)
            time.sleep(1.0) # Delay amigável
        else:
            logger.info("   ⚠️ Nada encontrado.")

    conn.close()
    logger.info("🏁 Ingestão concluída.")

if __name__ == "__main__":
    main()