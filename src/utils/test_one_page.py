import fitz
import sqlite3
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Configuração inicial
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_PATH = "database/harikatha.db"
PDF_PATH = "downloads/Sri_Slokamritam.pdf"

def test_extraction():
    print("🚀 Iniciando teste de extração única (Página 35)...")
    
    # 1. Abrir PDF e pegar texto da página 35 (índice 34)
    if not os.path.exists(PDF_PATH):
        print("❌ PDF não encontrado.")
        return
        
    doc = fitz.open(PDF_PATH)
    page_text = doc[34].get_text()
    
    # 2. Configurar Modelo 2.0 Flash Lite (Resiliente)
    model = genai.GenerativeModel(
        model_name='gemini-2.0-flash-lite',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    Extract verses from this text into a JSON list.
    Structure: [{{
      "chapter_number": int,
      "verse_number": int,
      "topic_name": "string",
      "internal_ref": "string",
      "sanskrit_roman": "string",
      "synonyms": "string",
      "translation": "string"
    }}]
    TEXT: {page_text}
    """
    
    try:
        print("📡 Enviando para Gemini...")
        response = model.generate_content(prompt)
        verses = json.loads(response.text)
        
        print(f"✅ Gemini retornou {len(verses)} versos.")
        
        # 3. Salvar no Banco
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for v in verses:
            ref = v.get('internal_ref') or f"{v.get('chapter_number')}.{v.get('verse_number')}"
            canon_id = f"SLOKA {ref}"
            
            # Inserir no índice (Book ID 9)
            cursor.execute("INSERT OR IGNORE INTO library_index (book_id, canonical_id, num_1, num_3) VALUES (9, ?, ?, ?)", 
                           (canon_id, v.get('chapter_number'), v.get('verse_number')))
            
            cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canon_id,))
            idx_id = cursor.fetchone()[0]
            
            # Inserir conteúdo
            if v.get('sanskrit_roman'):
                cursor.execute("INSERT INTO library_content (index_id, content_type, language_code, author_source, text_body) VALUES (?, 'MULA', 'sa-rom', 'TESTE', ?)", 
                               (idx_id, v['sanskrit_roman']))
            
            print(f"   💾 Gravado no banco: {canon_id}")
            
        conn.commit()
        conn.close()
        print("\n✨ Teste concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

if __name__ == "__main__":
    test_extraction()