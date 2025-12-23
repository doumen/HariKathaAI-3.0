#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
fix_slokamrtam_errors.py (Modo Interativo)
Script de Correção Cirúrgica.
Para cada erro detectado, solicita confirmação humana antes de alterar o banco.
"""

import sqlite3
import os
import re

# Configuração
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def ask_user(question):
    """Função auxiliar para input do usuário."""
    while True:
        resp = input(f"{question} [s/n/x=sair]: ").strip().lower()
        if resp == 's': return True
        if resp == 'n': return False
        if resp == 'x': 
            print("👋 Saindo...")
            exit(0)

def fix_references_in_root():
    """
    Interativo: Mostra a referência presa na raiz e pede para mover.
    """
    print(f"\n{'='*60}")
    print("🕵️‍♂️ FASE 1: REFERÊNCIAS PRESAS NA RAIZ")
    print(f"{'='*60}")

    conn = get_conn()
    cursor = conn.cursor()

    # Padrões de referências que costumam ficar presas
    patterns = [
        r'(\(SGG p\. \d+\))$',              # (SGG p. 152)
        r'(\(BR [\d\.]+ pt.*\))$',          # (BR 8.5 pt...)
        r'(\(Çrī Gauḍiyā Matha\).*)$',      # (Çrī Gauḍiyā Matha) siddha-
        r'(\d+\.[A-Z]\.\d+\(b\))$',         # 12.F.23(b)
        r'(\[.*philosophy\).+\])$',         # Editorial note
        r'(CC\s*Mad.*)$',                   # CCMad...
        r'(p\.139/BR.*)$'                   # p.139/BR...
    ]

    cursor.execute("""
        SELECT r.id, r.transliteration, t.id, t.source_ref, i.canonical_id
        FROM library_root_text r
        JOIN library_translations t ON r.index_id = t.index_id
        JOIN library_index i ON r.index_id = i.id
    """)
    rows = cursor.fetchall()

    for root_id, root_text, trans_id, current_ref, canon_id in rows:
        if not root_text: continue
        
        found_ref = None
        clean_root = root_text
        
        # Tenta casar com os padrões
        for pat in patterns:
            match = re.search(pat, root_text, re.IGNORECASE | re.DOTALL)
            if match:
                found_ref = match.group(1)
                clean_root = root_text.replace(found_ref, "").strip()
                break 
        
        if found_ref:
            print(f"\n📄 ID: {canon_id}")
            print(f"🔴 Raiz Atual:  ...{root_text[-50:] if len(root_text)>50 else root_text}")
            print(f"🟢 Nova Raiz:   ...{clean_root[-50:] if len(clean_root)>50 else clean_root}")
            print(f"➡️  Mover para Ref: '{found_ref}'")
            
            if ask_user("   Confirma correção?"):
                new_ref = f"{current_ref} {found_ref}".strip() if current_ref else found_ref
                cursor.execute("UPDATE library_root_text SET transliteration = ? WHERE id = ?", (clean_root, root_id))
                cursor.execute("UPDATE library_translations SET source_ref = ? WHERE id = ?", (new_ref, trans_id))
                conn.commit()
                print("   ✅ Feito.")
            else:
                print("   🚫 Ignorado.")
    
    conn.close()

def fix_broken_strings():
    """
    Interativo: Procura erros de texto (colado/explodido) e pede confirmação.
    """
    print(f"\n{'='*60}")
    print("🕵️‍♂️ FASE 2: CORREÇÃO DE TEXTO (TYPOS)")
    print(f"{'='*60}")
    
    replacements = {
        "v and e": "vande",
        "of fermy": "offer my",
        "of fer": "offer",
        "I of fer": "I offer",
        "Ioffer": "I offer",
        "praṇāmato": "praṇāma to",
        "thelotus": "the lotus",
        "feetof": "feet of",
        "ÇrīGuru": "Çrī Guru",
        "spiritualmaster": "spiritual master",
        "opulentlotus": "opulent lotus",
        "b r o t h e r": "brother",
        "o t h e r": "other",
        "w ith": "with",
        "t he": "the",
        "wit hin": "within",
        "kāma-bīja": "kāma-bīja" # As vezes quebra linha
    }

    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.id, t.text_body, t.word_for_word, i.canonical_id 
        FROM library_translations t
        JOIN library_index i ON t.index_id = i.id
    """)
    rows = cursor.fetchall()
    
    for row_id, body, w2w, canon_id in rows:
        new_body = body
        new_w2w = w2w
        modified = False
        
        # Verifica Corpo
        if new_body:
            for wrong, right in replacements.items():
                if wrong in new_body:
                    # Visualização do contexto
                    idx = new_body.find(wrong)
                    start = max(0, idx - 15)
                    end = min(len(new_body), idx + len(wrong) + 15)
                    context = new_body[start:end].replace('\n', ' ')
                    
                    print(f"\n📄 ID: {canon_id} (Corpo)")
                    print(f"🔍 Contexto: ...{context}...")
                    print(f"🔧 Trocar:   '{wrong}'  ->  '{right}'")
                    
                    if ask_user("   Confirma?"):
                        new_body = new_body.replace(wrong, right)
                        modified = True
                        print("   ✅ Alteração registrada (será salva ao final do registro).")
                    else:
                        print("   🚫 Ignorado.")
        
        # Verifica W2W
        if new_w2w:
            for wrong, right in replacements.items():
                if wrong in new_w2w:
                    idx = new_w2w.find(wrong)
                    start = max(0, idx - 15)
                    end = min(len(new_w2w), idx + len(wrong) + 15)
                    context = new_w2w[start:end].replace('\n', ' ')

                    print(f"\n📄 ID: {canon_id} (Word-for-Word)")
                    print(f"🔍 Contexto: ...{context}...")
                    print(f"🔧 Trocar:   '{wrong}'  ->  '{right}'")
                    
                    if ask_user("   Confirma?"):
                        new_w2w = new_w2w.replace(wrong, right)
                        modified = True
                        print("   ✅ Alteração registrada.")
                    else:
                        print("   🚫 Ignorado.")
        
        # Se houve alguma alteração confirmada neste registro, salva no banco
        if modified:
            cursor.execute("""
                UPDATE library_translations 
                SET text_body = ?, word_for_word = ? 
                WHERE id = ?
            """, (new_body, new_w2w, row_id))
            conn.commit()
            
    conn.close()

def manual_insert_missing_root():
    print(f"\n{'='*60}")
    print("🕵️‍♂️ FASE 3: VERSOS FALTANTES")
    print(f"{'='*60}")

    conn = get_conn()
    cursor = conn.cursor()
    
    target_id = "SLK_13.47"
    cursor.execute("""
        SELECT i.id, r.transliteration 
        FROM library_index i 
        LEFT JOIN library_root_text r ON i.id = r.index_id 
        WHERE i.canonical_id = ?
    """, (target_id,))
    res = cursor.fetchone()
    
    if res:
        idx_id, root = res
        if not root or len(root.strip()) == 0:
            print(f"\n⚠️ Verso {target_id} está VAZIO.")
            suggested_text = "kṛṣṇa-nāma-dhare kata bala?\nviṣaya-vāsanānale, mora citta sadā jvale,\nravi-tapta maru-bhūmi-tala"
            print(f"📜 Texto Sugerido:\n{suggested_text}")
            
            if ask_user("   Inserir este texto?"):
                cursor.execute("""
                    INSERT OR REPLACE INTO library_root_text (index_id, transliteration)
                    VALUES (?, ?)
                """, (idx_id, suggested_text))
                conn.commit()
                print("   ✅ Salvo.")
            else:
                print("   🚫 Ignorado.")
    
    conn.close()

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        try:
            fix_references_in_root()
            fix_broken_strings()
            manual_insert_missing_root()
            print("\n🏁 Processo de Correção Finalizado com Sucesso.")
        except KeyboardInterrupt:
            print("\n\n❌ Interrompido pelo usuário.")
    else:
        print("❌ Banco de dados não encontrado.")