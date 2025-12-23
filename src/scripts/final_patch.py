#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
final_patch.py
Correção manual definitiva para os versos problemáticos do Śrī Ślokāmṛtam.
Baseado na análise visual das imagens fornecidas (Versos 1.0 a 23.31).
"""

import sqlite3
import os

# Configuração
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def patch_verse(cursor, canon_id, root=None, ref=None, w2w=None):
    """Atualiza um verso específico com dados manuais."""
    print(f"🔧 Reparando {canon_id}...")
    
    # Busca o ID numérico
    cursor.execute("SELECT id FROM library_index WHERE canonical_id = ?", (canon_id,))
    res = cursor.fetchone()
    if not res:
        print(f"   ❌ Verso {canon_id} não encontrado no índice.")
        return
    index_id = res[0]

    # Atualiza Raiz (se fornecido)
    if root:
        # Verifica se já existe entrada na tabela root
        cursor.execute("SELECT id FROM library_root_text WHERE index_id = ?", (index_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE library_root_text SET transliteration = ? WHERE index_id = ?", (root.strip(), index_id))
        else:
            cursor.execute("INSERT INTO library_root_text (index_id, transliteration) VALUES (?, ?)", (index_id, root.strip()))

    # Atualiza Tradução/Ref/W2W (se fornecidos)
    if ref or w2w:
        cursor.execute("SELECT id FROM library_translations WHERE index_id = ?", (index_id,))
        res_trans = cursor.fetchone()
        
        if res_trans:
            trans_id = res_trans[0]
            if ref:
                cursor.execute("UPDATE library_translations SET source_ref = ? WHERE id = ?", (ref.strip(), trans_id))
            if w2w:
                cursor.execute("UPDATE library_translations SET word_for_word = ? WHERE id = ?", (w2w.strip(), trans_id))
        else:
            print(f"   ⚠️ Nenhuma tradução encontrada para {canon_id} para atualizar Ref/W2W.")

    print("   ✅ Feito.")

def run_patch():
    conn = get_conn()
    cursor = conn.cursor()

    # --- LISTA DE CORREÇÕES MANUAIS (Extraídas das Imagens) ---

    # 1.0 (Definição de Bhakti) - O caso mais crítico
    patch_verse(cursor, "SLK_1.0",
        root="""anyābhilāṣitā-śūnyaṁ
jñāna-karmādy-anāvṛtam
ānukūlyena kṛṣṇānu-
śīlanaṁ bhaktir uttamā""",
        ref="BRS 1.1.11/CC Mad 19.167/MS p.32/BRSB p.3/JD p.184/BTV p.6/BPKG Biog. p.364",
        w2w="anya-abhilāṣitā-śūnyam — without desires other than those for the service of Lord Kṛṣṇa (or without material desires, especially meat-eating, illicit sex, gambling and addiction to intoxicants); jñāna — knowledge aimed at impersonal liberation; karma — fruitive, reward seeking activities; ādi — artificial renunciation, yoga aimed at attaining mystic powers, and so on; anāvṛtam — not covered by; ānukūlyena — favourable; kṛṣṇa-anuśīlanaṁ — cultivation of service to Kṛṣṇa; bhaktiḥ uttamā — first-class devotional service. (The prefix ānu indicates ānugatya – ‘following, being under guidance’. Ānu also indicates ‘continuous, uninterrupted’)"
    )

    # 6.65 (Referência grudada)
    patch_verse(cursor, "SLK_6.65",
        root="""premadaṁ ca me kāmadaṁ ca me
vedanaṁ ca me vaibhavaṁ ca me
jīvanaṁ ca me jīvitaṁ ca me
daivataṁ ca me deva nā 'param""",
        ref="Śrī Kṛṣṇa-karṇāmṛtam 104/Śrī Vilāpa-kusumāñjaliḥ Nectar, vol. 2.6"
    )

    # 8.38 (Sahajiyas)
    patch_verse(cursor, "SLK_8.38",
        root="""ataḥ śrī-kṛṣṇa-nāmādi
na bhaved grāhyam indriyaiḥ
sevonmukhe hi jihvādau
svayam eva sphuraty adaḥ""",
        ref="Padma Purāṇa/ BRS 1.2.234/CC Mad 17.136/BR 2.32/BPKG Biog. p. 242, 330",
        w2w="ataḥ — therefore; śrī-kṛṣṇa-nāma-ādi — Lord Kṛṣṇa’s name, form, qualities, pastimes and so on; na — not; bhavet — can be; grāhyam — perceived; indriyaiḥ — by the blunt material senses; sevā-unmukhe — to one engaged in His service; hi — certainly; jihvā-ādau — beginning with the tongue; svayam — personally; eva — certainly; sphurati — become manifest; adaḥ — those (Kṛṣṇa’s name, form, qualities and so on)."
    )

    # 8.39 (Kirtana Prabhāve)
    patch_verse(cursor, "SLK_8.39",
        root="""kīrtana-prabhāve, smaraṇa haibe,
se kāle bhajana-nirjana sambhava""",
        ref="Mahājana-racita Gīta, Duṣṭa Mana! – Śrīla Bhaktisiddhānta Sarasvatī Prabhupāda",
        w2w="kīrtana-prabhāve — by the power of the chanting; smaraṇa — remembering the Lord’s pastimes; haibe — will be; se kāle — at that time; bhajana-nirjana — solitary bhajana; sambhava — possible."
    )

    # 13.87 (Kāma-gāyatrī)
    patch_verse(cursor, "SLK_13.87",
        root="""vṛndāvane ‘aprākṛta navīna madana’
kāma-gāyatrī kāma-bīje yāṅra upāsana""",
        ref="CC Mad 8.138",
        w2w="vṛndāvane — in Vṛndāvana; aprākṛta — spiritual; navīna — new; madana — Cupid; kāma-gāyatrī — hymns of desire; kāma-bīje — by the spiritual seed of desire called klīm; yāṅra — of whom; upāsana — the worship."
    )

    # 13.88 (Gopāla-mantra)
    patch_verse(cursor, "SLK_13.88",
        root="""tasmād oṁkāra-sambhūto
gopālo viśva-sambhavaḥ
klīm oṁkārasya caikatvaṁ
paṭhyate brahma-vādibhiḥ""",
        ref="" # Ref parece ter sido cortada no PDF ou não existe explícita na imagem
    )

    # 14.6 (Sintomas de Bhāva)
    patch_verse(cursor, "SLK_14.6",
        root="""kṣāntir avyartha-kālatvam viraktir māna-śūnyatā
āśā-bandhaḥ samutkaṇṭhā nāma-gāne sadā ruciḥ
āsaktis tad-guṇākhyāne prītis tad-vasati-sthale
ity ādayo ’nubhāvāḥ syur jāta-bhāvāṅkure jane""",
        ref="BRS-1.3.25-26 / CC Mad 23.18-19/BRSB–p.139/BR 6.3",
        w2w="kṣāntiḥ — forgiveness; avyartha-kālatvam — being free from wasting time; viraktiḥ — detachment; māna-śūnyatā — absence of false prestige; āśā-bandhaḥ — hope; samutkaṇṭhā — eagerness; nāma-gāne — in chanting the holy names; sadā — always; ruciḥ — taste; āsaktiḥ — attachment; tat — of Lord Kṛṣṇa; guṇa-ākhyāne — in describing the transcendental qualities; prītiḥ — affection; tat — His; vasati-sthale — for places of residence (the temple or holy places); iti — thus; ādayaḥ — and so on; anubhāvāḥ — the signs; syuḥ — are; jāta — developed; bhāva-aṅkure — whose seed of ecstatic emotion; jane — in a person."
    )

    # 22.20 (Kona bhāgye)
    patch_verse(cursor, "SLK_22.20",
        root="""kona bhāgye kona jīvera ‘śraddhā’ yadi haya
tabe sei jīva ‘sādhu-saṅga’ ye karaya
sādhu-saṅga haite haya ‘śravaṇa-kīrtana’
sādhana-bhaktye haya ‘sarvānartha-nivartana’
anartha-nivṛtti haile bhaktye ‘niṣṭhā’ haya
niṣṭhā haite śravaṇādye ‘ruci’ upajaya
ruci haite bhaktye haya ‘āsakti’ pracura
āsakti haite citte janme kṛṣṇe prīty-aṅkura
sei ‘bhāva’ gāḍha haile dhare ‘prema’-nāma
sei premā ‘prayojana’ sarvānanda-dhāma""",
        ref="CC Mad 23.9-13/PP p.83"
    )

    # 22.21 (Sādhya-vastu)
    patch_verse(cursor, "SLK_22.21",
        root="""‘sādhya-vastu’ ‘sādhana’ vinu keha nāhi pāya
kṛpā kari’ kaha, rāya, pābāra upāya""",
        ref="CC Mad 8.197/PP p.84"
    )

    # 22.46 (Hari-bhakti-mahādevyāḥ)
    patch_verse(cursor, "SLK_22.46",
        root="""hari-bhakti-mahādevyāḥ sarvā muktyādi-siddhayaḥ
bhuktayaś cādbhutās tasyāś ceṭikāvad anuvratāḥ""",
        ref="Nārada-pañcarātra/Bhakti-rasāmṛta-sindhu 1.1.34/VG p. 124/BTV p. 68"
    )

    # 23.31 (Vicitra-varṇa - O problema da numeração 23.31/23.30 no PDF)
    # Na imagem, o verso que começa com "vicitra-varṇa" está marcado como 23.31
    patch_verse(cursor, "SLK_23.31",
        root="""vicitra-varṇābharaṇābhirāme
’bhidhehi vaktrāmbuja-rāja-haṁsi
sadā madīye rasane ’graraṅge
govinda-dāmodara-mādhaveti (9)""",
        ref="" # Ref parece ser parte do texto ou implícita
    )

    conn.commit()
    conn.close()
    print("\n🏁 Todas as correções manuais foram aplicadas com sucesso.")

if __name__ == "__main__":
    run_patch()