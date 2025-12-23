#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
clean_slokamrtam_db.py
Script de Limpeza Pós-Ingestão.
Atua diretamente no SQLite para corrigir formatação sem precisar ler o PDF de novo.
"""

import sqlite3
import os
import re
import logging

# Configuração
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Cleaner")

def get_conn():
    return sqlite3.connect(DB_PATH)

# --- FUNÇÕES DE LIMPEZA ---

def fix_glued_english(text: str) -> str:
    """Separa palavras inglesas comuns que ficaram grudadas."""
    if not text: return None
    
    # 1. Lista Segura de Separação
    safe_splits = {
        "ofthe": "of the",
        "tothe": "to the",
        "inthe": "in the",
        "byme": "by me",
        "forme": "for me",
        "ofmy": "of my",
        "tomy": "to my",
        "isknown": "is known",
        "iscalled": "is called",
        "untothe": "unto the",
        "offermy": "offer my",
        "respectfulobeisances": "respectful obeisances"
    }
    
    # Substitui palavras inteiras (case insensitive seria ideal, mas simples resolve 90%)
    words = text.split()
    new_words = []
    for w in words:
        w_clean = w.strip('.,;')
        lower_w = w_clean.lower()
        
        if lower_w in safe_splits:
            fixed = safe_splits[lower_w]
            # Tenta preservar pontuação
            if w.endswith(';'): fixed += ';'
            elif w.endswith('.'): fixed += '.'
            elif w.endswith(','): fixed += ','
            new_words.append(fixed)
        else:
            new_words.append(w)
            
    text = " ".join(new_words)
    
    # 2. Espaço após pontuação (;a -> ; a)
    text = re.sub(r';([a-zA-Z])', r'; \1', text)
    
    return text

def format_w2w(text: str) -> str:
    """Formata o campo Word-for-Word."""
    if not text: return None
    
    # 1. Garante espaços ao redor do travessão
    # 'vande—offer' -> 'vande — offer'
    text = re.sub(r'\s*[—–−]\s*', ' — ', text)
    
    # 2. Aplica correção de inglês no lado direito (se possível)
    # Como é difícil saber onde começa o inglês sem quebrar o sânscrito,
    # aplicamos apenas a correção de pontuação e espaços gerais
    text = fix_glued_english(text)
    
    return text.strip()

def remove_leaked_titles(text: str) -> str:
    """Remove títulos que vazaram para o final da tradução."""
    if not text: return None
    
    lines = text.split('\n')
    if not lines: return text
    
    # Palavras-chave de títulos que costumam sobrar
    bad_endings = [
        "Samasta Pranama", "Pranama", "Tattva", "Vandana", 
        "Lila", "Astaka", "Gita", "Stotram", "Vijñapti", "Kirtana"
    ]
    
    # Checa a última linha
    last_line = lines[-1].strip()
    
    # Se a última linha for curta e contiver uma palavra-chave
    is_title = False
    if len(last_line) < 60 and not last_line.endswith('.'):
        for keyword in bad_endings:
            if keyword.lower() in last_line.lower():
                is_title = True
                break
    
    if is_title:
        logger.info(f"✂️  Cortando título vazado: '{last_line}'")
        return "\n".join(lines[:-1]).strip()
    
    return text

# --- LOOP PRINCIPAL ---

def clean_database():
    conn = get_conn()
    cursor = conn.cursor()
    
    # 1. Pega o ID do livro SLK
    cursor.execute("SELECT id FROM library_books WHERE acronym = 'SLK'")
    res = cursor.fetchone()
    if not res:
        print("Livro SLK não encontrado.")
        return
    book_id = res[0]
    
    print(f"🧹 Iniciando limpeza para o livro ID {book_id} (SLK)...")
    
    # 2. Seleciona todas as traduções desse livro
    query = """
        SELECT t.id, t.text_body, t.word_for_word 
        FROM library_translations t
        JOIN library_index i ON t.index_id = i.id
        WHERE i.book_id = ?
    """
    cursor.execute(query, (book_id,))
    rows = cursor.fetchall()
    
    updates = 0
    
    for row_id, body, w2w in rows:
        original_body = body
        original_w2w = w2w
        
        # APLICA LIMPEZAS
        new_body = remove_leaked_titles(body)
        new_body = fix_glued_english(new_body) # Opcional no corpo, mas bom pra garantir
        
        new_w2w = format_w2w(w2w)
        
        # VERIFICA MUDANÇAS
        has_change = False
        
        if new_body != original_body:
            has_change = True
            
        if new_w2w != original_w2w:
            has_change = True
            # logger.info(f"W2W Cleaned: \n   ANTES: {original_w2w[:50]}...\n   DEPOIS: {new_w2w[:50]}...")

        if has_change:
            cursor.execute("""
                UPDATE library_translations 
                SET text_body = ?, word_for_word = ? 
                WHERE id = ?
            """, (new_body, new_w2w, row_id))
            updates += 1
            
    conn.commit()
    conn.close()
    
    print(f"\n✅ Concluído! {updates} registros foram limpos e atualizados.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        clean_database()
    else:
        print("Banco de dados não encontrado.")