"""
Como Rodar

    Coloque o arquivo bhagavad-gita-4ed-eng.pdf na pasta raiz do projeto.

    Execute:
    PowerShell

py src/scripts/miner_pdf_gita.py
"""

import pdfplumber
import re
import sqlite3
import os
import sys

# Setup de caminhos
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

from src.intelligence.librarian_storage import _ensure_book_id, _ensure_index_id, _upsert_translation, _upsert_commentary

DB_PATH = os.path.join(project_root, "database", "harikatha.db")
PDF_PATH = "bhagavad-gita-4ed-eng.pdf" # O arquivo que você enviou

def save_verse_data(verse_data):
    """Salva os dados extraídos no Banco de Dados"""
    if not verse_data['ref']: return

    print(f"💾 Salvando BG {verse_data['ref']}...")
    conn = sqlite3.connect(DB_PATH)
    try:
        # 1. Garante IDs
        book_id = _ensure_book_id(conn, "BG") # Bhagavad-gita
        canonical_id = f"BG_{verse_data['ref']}"
        index_id = _ensure_index_id(conn, book_id, canonical_id, verse_data['ref'])

        # 2. Salva Tradução (Inglês)
        if verse_data['translation']:
            full_translation = "\n".join(verse_data['translation'])
            _upsert_translation(conn, index_id, 'en', 'BV Narayana Maharaja', full_translation)

        # 3. Salva Comentário (Inglês)
        if verse_data['commentary']:
            full_commentary = "\n".join(verse_data['commentary'])
            # Tenta detectar se é Visvanatha ou Narayana Maharaja pelo título, 
            # ou salva como genérico da edição
            _upsert_commentary(conn, index_id, 'en', 'Sarartha-varsini (Gita)', full_commentary)

        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao salvar {verse_data['ref']}: {e}")
    finally:
        conn.close()

def mine_gita_pdf():
    print(f"🔨 Iniciando mineração de: {PDF_PATH}")
    
    current_verse = {"ref": None, "translation": [], "commentary": []}
    state = "SEARCHING" # SEARCHING, TRANSLATION, COMMENTARY
    
    # Regex para detectar "VERSE 2.12" ou "Verse 2.12"
    verse_pattern = re.compile(r'^(VERSE|Verse)\s+(\d+\.\d+)')
    
    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        
        # Pula as primeiras páginas de introdução (ajuste conforme necessário)
        for i, page in enumerate(pdf.pages[50:], start=51): 
            text = page.extract_text()
            if not text: continue
            
            # Filtra cabeçalhos/rodapés repetitivos (Ex: Título do livro no topo)
            lines = text.split('\n')
            
            for line in lines:
                clean = line.strip()
                
                # --- DETECTOR DE VERSO ---
                match = verse_pattern.search(clean)
                if match:
                    # Se já tínhamos um verso capturado, salva ele agora
                    if current_verse['ref']:
                        save_verse_data(current_verse)
                    
                    # Reseta para o novo verso
                    new_ref = match.group(2)
                    print(f"   📍 Encontrado: {new_ref} (Pág {i})")
                    current_verse = {"ref": new_ref, "translation": [], "commentary": []}
                    state = "WAITING_TRANSLATION" # Ignora sânscrito por enquanto, foca na tradução
                    continue

                # --- MÁQUINA DE ESTADOS ---
                
                if state == "WAITING_TRANSLATION":
                    if clean.upper() == "TRANSLATION":
                        state = "READING_TRANSLATION"
                
                elif state == "READING_TRANSLATION":
                    # Se achar "COMMENTARY" ou "PURPORT", troca de estado
                    if "COMMENTARY" in clean.upper() or "PURPORT" in clean.upper():
                        state = "READING_COMMENTARY"
                    else:
                        current_verse['translation'].append(clean)
                
                elif state == "READING_COMMENTARY":
                    # O comentário vai até achar o próximo verso (no topo do loop)
                    # ou alguma seção de fim de capítulo (opcional)
                    current_verse['commentary'].append(clean)

        # Salva o último verso
        if current_verse['ref']:
            save_verse_data(current_verse)

if __name__ == "__main__":
    # Garante que o livro BG existe no banco antes de começar
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO library_books (acronym, book_title) VALUES ('BG', 'Śrīmad Bhagavad-gītā')")
    conn.commit()
    conn.close()
    
    mine_gita_pdf()