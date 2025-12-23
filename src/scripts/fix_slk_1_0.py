#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
fix_slk_1_0.py
Correção manual e definitiva para o verso SLK_1.0 (Uttama-bhakti),
que sofreu fragmentação severa durante a extração.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def fix_entry():
    conn = get_conn()
    cursor = conn.cursor()
    
    target_id = "SLK_1.0"
    print(f"🔧 Reparando {target_id} com dados manuais da imagem...")

    # 1. Obter IDs
    cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (target_id,))
    res = cursor.fetchone()
    if not res:
        print("❌ Verso não encontrado.")
        return
    index_id = res[0]

    # --- DADOS CORRETOS (Extraídos da Imagem) ---
    
    # Sânscrito Limpo
    clean_root = """anyābhilāṣitā-śūnyaṁ
jñāna-karmādy-anāvṛtam
ānukūlyena kṛṣṇānu-
śīlanaṁ bhaktir uttamā"""

    # Referência Completa
    clean_ref = "BRS 1.1.11/CC Mad 19.167/MS p.32/BRSB p.3/JD p.184/BTV p.6/BPKG Biog. p.364"

    # W2W Completo (Juntando o começo que você tem com o fim que estava na raiz)
    clean_w2w = """anya-abhilāṣitā-śūnyam — without desires other than those for the service of Lord Kṛṣṇa (or without material desires, especially meat-eating, illicit sex, gambling and addiction to intoxicants); jñāna — knowledge aimed at impersonal liberation; karma — fruitive, reward seeking activities; ādi — artificial renunciation, yoga aimed at attaining mystic powers, and so on; anāvṛtam — not covered by; ānukūlyena — favourable; kṛṣṇa-anuśīlanaṁ — cultivation of service to Kṛṣṇa; bhaktiḥ uttamā — first-class devotional service. (The prefix ānu indicates ānugatya – ‘following, being under guidance’. Ānu also indicates ‘continuous, uninterrupted’)"""

    # Tradução do Corpo (Estava correta no PDF, garantindo que esteja no banco)
    clean_body = """Uttama-bhakti, pure devotional service, is the cultivation of activities that are meant exclusively for the pleasure of Śrī Kṛṣṇa. In other words, it is the uninterrupted flow of service to Śrī Kṛṣṇa, performed through all endeavors of body, mind and speech, as well as through the expression of various spiritual sentiments (bhāvas). It is not covered by jñāna (knowledge aimed at impersonal liberation), karma (reward-seeking activity), yoga or austerities; and it is completely free from all desires other than the aspiration to bring happiness to Śrī Kṛṣṇa."""

    # 2. Atualizar Raiz
    cursor.execute("UPDATE library_root_text SET transliteration = ? WHERE index_id = ?", (clean_root, index_id))

    # 3. Atualizar Tradução (W2W, Ref, Body)
    # Verifica se já existe tradução para dar update, senão insert
    cursor.execute("SELECT id FROM library_translations WHERE index_id = ?", (index_id,))
    trans_res = cursor.fetchone()

    if trans_res:
        trans_id = trans_res[0]
        cursor.execute("""
            UPDATE library_translations 
            SET text_body = ?, word_for_word = ?, source_ref = ?
            WHERE id = ?
        """, (clean_body, clean_w2w, clean_ref, trans_id))
    else:
        cursor.execute("""
            INSERT INTO library_translations (index_id, language, text_body, word_for_word, source_ref)
            VALUES (?, 'en', ?, ?, ?)
        """, (index_id, clean_body, clean_w2w, clean_ref))

    conn.commit()
    conn.close()
    print("✅ SLK_1.0 reparado com sucesso!")

if __name__ == "__main__":
    fix_entry()