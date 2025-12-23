import sqlite3
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega a API KEY
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "database", "harikatha.db")

def get_verses_for_gaudiya_translation():
    """
    Busca versos que têm Sânscrito e Referência em Inglês (WisdomLib),
    mas ainda não têm a tradução Gaudiya em Português.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Seleciona o verso se ele tem raiz, tem inglês (para apoio), 
    # mas NÃO tem tradução feita pelo 'AI_Gaudiya_PT'
    sql = """
    SELECT 
        i.id, 
        i.canonical_id, 
        r.primary_script as sanskrit, 
        r.transliteration,
        t_en.text_body as english_ref
    FROM library_index i
    JOIN library_root_text r ON r.index_id = i.id
    JOIN library_translations t_en ON t_en.index_id = i.id 
         AND t_en.language_code = 'en'
    WHERE NOT EXISTS (
        SELECT 1 FROM library_translations t_pt 
        WHERE t_pt.index_id = i.id 
        AND t_pt.language_code = 'pt' 
        AND t_pt.translator = 'AI_Gaudiya_PT' -- Nosso tradutor especializado
    )
    GROUP BY i.id
    LIMIT 5
    """
    
    rows = cur.execute(sql).fetchall()
    conn.close()
    return rows

def save_translation(index_id, text):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO library_translations
            (index_id, language_code, translator, text_body)
            VALUES (?, ?, ?, ?)
        """, (index_id, 'pt', 'AI_Gaudiya_PT', text.strip()))
        conn.commit()
        print(f"   ✅ Salvo como 'AI_Gaudiya_PT'")
    except Exception as e:
        print(f"   ❌ Erro ao salvar: {e}")
    finally:
        conn.close()

def consult_scholar(verse_data):
    index_id, canonical_id, sanskrit, translit, english_ref = verse_data
    
    print(f"\n📿 Meditando sobre {canonical_id}...")
    
    # --- O PROMPT GAUDIYA ---
    # Instruímos a IA a priorizar a teologia (Siddhanta) sobre a tradução literal.
    prompt = f"""
    Atue como um Pandita e tradutor devoto da tradição Gaudiya Vaishnava (seguidor de Rupa Goswami e Srila Prabhupada).
    
    TAREFA:
    Traduza o verso abaixo do Sânscrito para o Português do Brasil.
    
    DADOS:
    - Sânscrito: {sanskrit}
    - Transliteração: {translit}
    - Referência Acadêmica (Inglês): "{english_ref}" (Use APENAS para tirar dúvidas gramaticais. Ignore se for seco ou impessoal).
    
    DIRETRIZES DE TRADUÇÃO (Siddhanta):
    1. O Foco é BHAKTI (Devoção). Não use termos impessoais ou monistas.
    2. Se o verso falar de Krishna/Radha, use a linguagem doce e respeitosa dos Acaryas.
    3. Mantenha termos técnicos essenciais em Sânscrito (como 'Rasa', 'Preman', 'Bhava') se não houver equivalente perfeito, ou coloque a tradução entre parênteses.
    4. Estilo: Elevado, mas compreensível para um devoto brasileiro atual.
    
    SAÍDA:
    Apenas o texto da tradução em Português.
    """

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        translation = response.text.strip()
        
        # Remove aspas extras se a IA colocar
        if translation.startswith('"') and translation.endswith('"'):
            translation = translation[1:-1]
            
        print(f"   📜 Resultado: {translation[:100]}...")
        save_translation(index_id, translation)
        
    except Exception as e:
        print(f"   ❌ O Pandita silenciou (Erro): {e}")

if __name__ == "__main__":
    print("🙏 Scholar Gaudiya iniciado...")
    verses = get_verses_for_gaudiya_translation()
    
    if not verses:
        print("📭 Todos os versos já possuem tradução Gaudiya.")
    else:
        print(f"📚 Encontrados {len(verses)} versos para traduzir.")
        for v in verses:
            consult_scholar(v)