import fitz
import sqlite3
import json
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# CONFIGURAÇÕES
DB_PATH = "database/harikatha.db"
PDF_PATH = "Gaudiya-Giti-guccha-7th-ed-2016.pdf"
BOOK_ID = 10  # Verifique se este ID está livre ou crie um novo para o Giti Guccha

def parse_song_page(text, page_num):
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    Analyze this page from 'Gaudiya Giti-guccha'. Extract songs into JSON.
    Songs often have a title, an author, and numbered stanzas.
    
    STRUCTURE:
    [{{
      "title": "string",
      "author": "string",
      "section": "string",
      "content": [
        {{
          "stanza_number": int,
          "original_text": "string",
          "translation": "string"
        }}
      ]
    }}]
    TEXT: {text}
    """
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"⚠️ Erro na página {page_num}: {e}")
        return None

def save_song_to_db(conn, song, page_num):
    cursor = conn.cursor()
    title = song.get('title', 'Unknown Title')
    author = song.get('author', 'Unknown Author')
    
    # Criamos um canonical_id baseado no título
    canon_id = f"GITI {title[:20].upper().replace(' ', '_')}"

    # 1. Inserir no Índice
    cursor.execute('''
        INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_2) 
        VALUES (?, ?, ?)
    ''', (BOOK_ID, canon_id, page_num))
    
    cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canon_id,))
    idx_id = cursor.fetchone()[0]

    # 2. Inserir Estrofes
    for stanza in song.get('content', []):
        body = f"[{stanza.get('stanza_number')}] {stanza.get('original_text')}"
        
        # Original (Bengali/Sânscrito)
        cursor.execute('''
            INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body)
            VALUES (?, 'MULA', 'bn', ?, ?)
        ''', (idx_id, author, body))
        
        # Tradução (se houver)
        if stanza.get('translation'):
            cursor.execute('''
                INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body)
                VALUES (?, 'TRANSLATION', 'en', ?, ?)
            ''', (idx_id, author, stanza.get('translation')))

    conn.commit()
    print(f"✅ Canção Salva: {title}")

def main():
    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF não encontrado: {PDF_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    doc = fitz.open(PDF_PATH)
    
    print(f"🚀 Iniciando ingestão do Giti-guccha ({len(doc)} páginas)...")
    
    # Sugestão: Começar após o índice (ex: página 20)
    for i in range(20, len(doc)):
        print(f"📄 Processando página {i+1}...")
        text = doc[i].get_text()
        
        if len(text) < 100: continue
        
        songs = parse_song_page(text, i+1)
        if songs:
            if isinstance(songs, list):
                for s in songs: save_song_to_db(conn, s, i+1)
            else:
                save_song_to_db(conn, songs, i+1)
        
        # Como você é Tier 1, um delay de 2s é seguro e rápido
        time.sleep(2)

if __name__ == "__main__":
    main()