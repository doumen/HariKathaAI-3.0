"""
Este script vai ler as últimas páginas do PDF (onde geralmente está o índice), 
extrair os termos e salvá-los na tabela theological_concepts.

Nota: Você precisará abrir o PDF manualmente uma vez para ver 
em qual página começa o "General Index" (digamos, página 900).

Como integrar isso ao fluxo?

    Descubra as Páginas: Abra o bhagavad-gita-4ed-eng.pdf. Vá até o final. Ache onde começa o "General Index". Anote o número da página (digamos, 1050) e coloque na variável START_PAGE do script acima.

    Rode o Minerador:
    PowerShell

    py src/scripts/miner_glossary.py

    Resultado: Sua tabela theological_concepts vai pular de 20 termos para 2.000 termos (ex: Abhidheya, Acintya-bhedabheda, Goloka, Gopis...).

    Rode o Gold Washer: Agora, rode novamente o py src/intelligence/gold_washer.py. Como a lista de conceitos agora é gigante e vinda do próprio livro, o "tagueamento" das suas aulas e versos será infinitamente mais preciso.

E sobre o "Quoted Verses"?

Para o índice de versos citados (quoted verses), a lógica é similar, mas o valor dele é maior para Validação Cruzada.

Podemos fazer um script futuro que lê esse índice e verifica: "O índice diz que o verso SB 1.2.11 foi citado na página 450. Será que nosso minerador de texto encontrou essa citação?"

Mas, por enquanto, focar no General Index vai dar um "cérebro" enorme para a sua IA entender o vocabulário Gaudiya.
"""

import pdfplumber
import re
import sqlite3
import os
import sys

# Setup de diretórios
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

DB_PATH = os.path.join(project_root, "database", "harikatha.db")
PDF_PATH = "bhagavad-gita-4ed-eng.pdf" # Seu arquivo

# CONFIGURE AQUI: Onde começa e termina o índice no seu PDF?
# (Abra o PDF e olhe o número "absoluto" da página no leitor)
START_PAGE = 1050  # Exemplo: página onde começa "General Index"
END_PAGE = 1100    # Exemplo: página final

def save_concepts(concepts):
    conn = sqlite3.connect(DB_PATH)
    count = 0
    try:
        for term in concepts:
            # Limpeza: remove pontos finais, números e espaços extras
            clean_term = term.strip().strip('.').strip()
            
            # Pula termos muito curtos ou numéricos
            if len(clean_term) < 3 or clean_term.isdigit(): continue
            
            # Tenta categorizar automaticamente (básico)
            category = "General"
            if clean_term[0].isupper(): category = "Proper Noun" # Nomes próprios
            
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO theological_concepts (term, category) 
                    VALUES (?, ?)
                """, (clean_term, category))
                count += 1
            except sqlite3.Error: pass
            
        conn.commit()
        print(f"✅ {count} novos conceitos adicionados à Ontologia.")
    finally:
        conn.close()

def mine_index():
    print(f"⛏️  Minerando Índice do PDF (Págs {START_PAGE}-{END_PAGE})...")
    
    found_terms = set()
    
    # Regex para pegar linhas de índice típicas: "Termo ............ 123, 456"
    # Grupo 1: O Texto
    # Grupo 2: Os Pontinhos (opcional)
    # Grupo 3: Os Números
    index_pattern = re.compile(r'^([A-Za-zāīūṛṭḍṇśṣṁḥĀĪŪṚṬḌṆŚṢṀḤ\s\(\)\-]+?)(?:\.{2,}|,)\s*(\d+.*)$')

    with pdfplumber.open(PDF_PATH) as pdf:
        # Itera apenas nas páginas do índice
        # pdfplumber usa index 0, então subtraímos 1
        pages_to_process = pdf.pages[START_PAGE-1 : END_PAGE]
        
        for page in pages_to_process:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                match = index_pattern.search(line.strip())
                if match:
                    term = match.group(1)
                    found_terms.add(term)
                    # print(f"   Termo: {term}") # Debug

    print(f"📚 Total de termos brutos encontrados: {len(found_terms)}")
    save_concepts(found_terms)

if __name__ == "__main__":
    mine_index()