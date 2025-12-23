#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
audit_slokamrtam.py
Ferramenta de diagnóstico para encontrar anomalias no banco harikatha.db
"""

import sqlite3
import os
import sys

# Configuração
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def run_query(title, query, params=()):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'-'*60}")
    
    if not rows:
        print("✅ Nenhum caso problemático encontrado!")
    else:
        print(f"⚠️ Encontrados {len(rows)} casos:")
        for row in rows[:20]: # Mostra só os primeiros 20 para não poluir
            print(row)
        if len(rows) > 20:
            print(f"... e mais {len(rows) - 20} registros.")

# --- CONSULTAS DE AUDITORIA ---

def check_missing_root():
    """1. Versos que têm índice, mas NÃO têm texto raiz (Sânscrito/Bengali)"""
    query = """
        SELECT i.canonical_id 
        FROM library_index i
        LEFT JOIN library_root_text r ON i.id = r.index_id
        WHERE r.transliteration IS NULL OR length(r.transliteration) < 2
        ORDER BY i.id;
    """
    run_query("Versos SEM Texto Raiz (Root❌)", query)

def check_missing_translation():
    """2. Versos sem corpo de tradução E sem referência (Fantasmas)"""
    query = """
        SELECT i.canonical_id 
        FROM library_index i
        LEFT JOIN library_translations t ON i.id = t.index_id
        WHERE (t.text_body IS NULL OR length(t.text_body) < 2)
          AND (t.source_ref IS NULL OR length(t.source_ref) < 2)
    """
    run_query("Versos SEM Tradução nem Referência", query)

def check_dirty_encoding():
    """3. Procura caracteres Balarama que escaparam da limpeza (ä, ö, ñ, etc)"""
    # Lista de chars comuns do Balarama que não deveriam existir no IAST limpo
    dirty_chars = ['ä', 'ü', 'å', 'è', 'ì', 'ï', 'ö', 'ò', 'ë', 'ç']
    
    conditions = " OR ".join([f"transliteration LIKE '%{c}%'" for c in dirty_chars])
    
    query = f"""
        SELECT i.canonical_id, r.transliteration
        FROM library_root_text r
        JOIN library_index i ON r.index_id = i.id
        WHERE {conditions}
    """
    run_query("Sujeira de Encoding (Balarama não convertido)", query)

def check_merged_references():
    """4. Verifica se a Referência ficou grudada no Texto Raiz"""
    # Procura por "SB " ou "CC " ou "p." dentro do texto raiz
    query = """
        SELECT i.canonical_id, substr(r.transliteration, -30) as final_do_texto
        FROM library_root_text r
        JOIN library_index i ON r.index_id = i.id
        WHERE r.transliteration LIKE '%SB %' 
           OR r.transliteration LIKE '%CC %'
           OR r.transliteration LIKE '% p.%'
           OR r.transliteration LIKE '%Vol.%'
    """
    run_query("Texto Raiz com Referência Grudada", query)

def check_w2w_quality():
    """5. Verifica se o W2W foi separado corretamente"""
    query = """
        SELECT i.canonical_id, substr(t.word_for_word, 0, 50) || '...'
        FROM library_translations t
        JOIN library_index i ON t.index_id = i.id
        WHERE t.word_for_word IS NOT NULL
        LIMIT 10
    """
    run_query("Amostra de Word-for-Word (Verifique se parece dicionário)", query)

def check_leaked_titles():
    """6. Títulos vazados no final da tradução"""
    # Procura traduções que terminam com palavras suspeitas sem pontuação final
    keywords = ['Pranama', 'Tattva', 'Vandana', 'Lila', 'Astaka']
    conditions = " OR ".join([f"text_body LIKE '%{k}'" for k in keywords])
    
    query = f"""
        SELECT i.canonical_id, substr(t.text_body, -50)
        FROM library_translations t
        JOIN library_index i ON t.index_id = i.id
        WHERE ({conditions})
    """
    run_query("Possíveis Títulos Vazados no Fim da Tradução", query)

def check_stats():
    """Estatísticas Gerais"""
    conn = get_conn()
    cur = conn.cursor()
    
    total_index = cur.execute("SELECT count(*) FROM library_index").fetchone()[0]
    total_root = cur.execute("SELECT count(*) FROM library_root_text").fetchone()[0]
    total_trans = cur.execute("SELECT count(*) FROM library_translations").fetchone()[0]
    total_w2w = cur.execute("SELECT count(*) FROM library_translations WHERE word_for_word IS NOT NULL").fetchone()[0]
    
    print(f"\n{'='*60}")
    print("📊 ESTATÍSTICAS GERAIS")
    print(f"{'-'*60}")
    print(f"Versos Indexados:   {total_index}")
    print(f"Textos Raiz:        {total_root}")
    print(f"Traduções (Corpo):  {total_trans}")
    print(f"Word-for-Word:      {total_w2w}")
    print(f"{'='*60}\n")
    conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("❌ Banco de dados não encontrado.")
    else:
        check_stats()
        check_missing_root()
        check_dirty_encoding()
        check_merged_references()
        check_leaked_titles()
        check_w2w_quality()