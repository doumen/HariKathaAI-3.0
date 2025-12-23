#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
final_cleanup.py
Script final para resolver os últimos 4 problemas pendentes.
Correções aplicadas:
1. Ajuste de nomes de colunas para bater com Schema V8.0 (language -> language_code).
2. Remoção de colunas inexistentes no índice (chapter_title).
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def ensure_slk_8_39_exists(cursor, book_id):
    """Insere o registro do verso 8.39 na tabela de índice e depois insere o conteúdo."""
    canonical_id = "SLK_8.39"
    
    # 1. Verifica se existe no índice
    cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canonical_id,))
    res = cursor.fetchone()
    
    if not res:
        print(f"➕ Criando entrada no índice para {canonical_id}...")
        # Schema V8.0: library_index só tem book_id e canonical_id (e nums opcionais)
        cursor.execute("""
            INSERT INTO library_index (book_id, canonical_id)
            VALUES (?, ?)
        """, (book_id, canonical_id))
        index_id = cursor.lastrowid
    else:
        index_id = res[0]
        
    # 2. Insere/Atualiza Raiz
    root_text = """kīrtana-prabhāve, smaraṇa haibe,
se kāle bhajana-nirjana sambhava"""
    
    cursor.execute("INSERT OR REPLACE INTO library_root_text (index_id, transliteration) VALUES (?, ?)", 
                   (index_id, root_text))

    # 3. Insere/Atualiza Tradução
    w2w = "kīrtana-prabhāve — by the power of the chanting; smaraṇa — remembering the Lord’s pastimes; haibe — will be; se kāle — at that time; bhajana-nirjana — solitary bhajana; sambhava — possible."
    body = "The transcendental power of congregational chanting automatically awakens remembrance of the Lord and His divine pastimes in relation to one’s own eternal spiritual form. Only at that time does it become possible to go off to a solitary place and engage in the confidential worship of Their Lordships (aṣṭa-kālīya-līlā-smaraṇa)."
    source_ref = "Mahājana-racita Gīta, Duṣṭa Mana! – Śrīla Bhaktisiddhānta Sarasvatī Prabhupāda"
    
    # Verifica se já tem tradução
    cursor.execute("SELECT id FROM library_translations WHERE index_id = ?", (index_id,))
    trans_res = cursor.fetchone()
    
    if trans_res:
        cursor.execute("""
            UPDATE library_translations SET text_body=?, word_for_word=?, source_ref=? WHERE id=?
        """, (body, w2w, source_ref, trans_res[0]))
    else:
        # CORREÇÃO CRÍTICA: language -> language_code
        cursor.execute("""
            INSERT INTO library_translations (index_id, language_code, text_body, word_for_word, source_ref)
            VALUES (?, 'en', ?, ?, ?)
        """, (index_id, body, w2w, source_ref))
        
    print("✅ SLK_8.39 restaurado com sucesso.")

def fix_slk_0_1(cursor):
    """Substitui o texto explodido do 0.1 por texto limpo."""
    print("🔧 Consertando SLK_0.1 (Explodido)...")
    
    w2w = "vande — offer my respectful obeisances; aham — I; śrī-guroḥ — of Śrī Gurudeva; śrī-yuta-pada-kamalam — unto the opulent lotus feet; śrī-gurun — unto the spiritual masters; vaiṣṇavān — unto the Vaiṣṇavas; ca — and; śrī-rūpam — unto Śrīla Rūpa Gosvāmī; sāgrajātam — with his elder brother (Śrīla Sanātana Gosvāmī); saha-gaṇa-raghunāthan-vitam — with Raghunātha Dāsa Gosvāmī and associates; tam — unto him; sa-jīvam — with Jīva Gosvāmī; sādvaitam — with Advaita Ācārya; sāvadhūtam — with Nityānanda Prabhu; parijana-sahitam — and with Śrīvāsa Ṭhākura and all the other devotees; kṛṣṇa-caitanya-devam — unto Lord Śrī Kṛṣṇa Caitanya Mahāprabhu; śrī-rādhā-kṛṣṇa-pādān — unto the lotus feet of Śrī Rādhā and Kṛṣṇa; saha-gaṇa-lalitā-śrī-viśākhān-vitāṁś — with Lalitā, Viśākhā and the other sakhīs; ca — also."
    
    body = "I offer praṇāma to the lotus feet of Śrī Gurudeva (both dīkṣā and śikṣā-guru), guru-varga (our entire disciplic succession), the Vaiṣṇavas, Śrīla Rūpa Gosvāmī, his elder brother Śrīla Sanātana Gosvāmī, Śrīla Raghunātha Dāsa Gosvāmī, Śrīla Jīva Gosvāmī and their associates. I offer praṇāma to Śrī Advaita Ācārya, Śrī Nityānanda Prabhu, Śrīvāsa Ṭhākura and all the devotees, and to Śrī Kṛṣṇa Caitanya Mahāprabhu. I offer praṇāma to the lotus feet of Śrī Rādhā and Kṛṣṇa, and to Śrī Lalitā-devī, Śrī Viśākhā-devī and all the other sakhīs."

    cursor.execute("SELECT id FROM library_index WHERE canonical_id = 'SLK_0.1'")
    res = cursor.fetchone()
    if res:
        index_id = res[0]
        cursor.execute("""
            UPDATE library_translations 
            SET word_for_word = ?, text_body = ? 
            WHERE index_id = ?
        """, (w2w, body, index_id))
        print("✅ SLK_0.1 limpo.")

def fix_slk_13_47(cursor):
    """Insere o texto raiz do 13.47."""
    print("🔧 Preenchendo SLK_13.47...")
    root_text = """kṛṣṇa-nāma-dhare kata bala?
viṣaya-vāsanānale, mora citta sadā jvale,
ravi-tapta maru-bhūmi-tala"""
    
    cursor.execute("SELECT id FROM library_index WHERE canonical_id = 'SLK_13.47'")
    res = cursor.fetchone()
    if res:
        # Tenta update primeiro
        cursor.execute("UPDATE library_root_text SET transliteration = ? WHERE index_id = ?", (root_text, res[0]))
        # Se não afetou nenhuma linha (não existia), faz insert
        if cursor.rowcount == 0:
             cursor.execute("INSERT INTO library_root_text (index_id, transliteration) VALUES (?, ?)", (res[0], root_text))
        print("✅ SLK_13.47 preenchido.")

def fix_slk_13_87(cursor):
    """Remove título vazado no 13.87."""
    print("🔧 Limpando SLK_13.87...")
    cursor.execute("""
        SELECT t.id, t.text_body 
        FROM library_translations t
        JOIN library_index i ON t.index_id = i.id
        WHERE i.canonical_id = 'SLK_13.87'
    """)
    res = cursor.fetchone()
    if res:
        trans_id, body = res
        if "Rādhā-Kṛṣṇa tattva" in body:
            # Remove o título do final
            clean_body = body.split("therefore kāma-bīja")[0].strip() + " therefore kāma-bīja indicates Rādhā-Kṛṣṇa tattva."
            clean_body = clean_body.replace("\nindicates", " indicates").strip()
            
            cursor.execute("UPDATE library_translations SET text_body = ? WHERE id = ?", (clean_body, trans_id))
            print("✅ SLK_13.87 ajustado.")

def run_cleanup():
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM library_books WHERE acronym = 'SLK'")
    book_res = cursor.fetchone()
    if not book_res:
        print("Livro SLK não encontrado.")
        return
    book_id = book_res[0]

    ensure_slk_8_39_exists(cursor, book_id)
    fix_slk_0_1(cursor)
    fix_slk_13_47(cursor)
    fix_slk_13_87(cursor)
    
    conn.commit()
    conn.close()
    print("\n✨ Limpeza final concluída!")

if __name__ == "__main__":
    run_cleanup()