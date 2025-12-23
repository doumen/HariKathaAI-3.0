"""
Os Desafios do PDF (E como resolver)

    Cabeçalhos e Rodapés: O PDF repete o título do livro no topo de toda página. Isso suja o texto (ex: no meio de um Purport aparece "BHAKTI RASAMRTA SINDHU").

        Solução: O pdfplumber permite definir uma "área de corte" (crop box) para ignorar os primeiros 5% e os últimos 5% da página.

    Hifenização: Palavras quebradas no final da linha (ex: "Krs-na").

        Solução: No momento de salvar, rodamos um script simples para juntar: text.replace("- ", "").

    Layouts de Coluna Dupla: Se o PDF for antigo e tiver duas colunas de texto.

        Solução: O pdfplumber tem configurações avançadas para ler coluna esquerda, depois direita.

Veredito

Vale a pena fazer isso SE você tiver PDFs de alta qualidade (texto selecionável) e se a fonte (WisdomLib) não tiver o conteúdo que você quer (como os comentários de Srila Prabhupada ou dos Goswamis que só existem em livros impressos).

Se o WisdomLib já tem o comentário (Purport), é 100x mais fácil ajustar o Scraper Web que fizemos antes para pegar o texto após a tradução, do que brigar com PDFs.

Quer tentar ajustar o Scraper Web primeiro para pegar os comentários? (É mais garantido)."""

import pdfplumber
import re

def mine_pdf_book(pdf_path):
    print(f"📄 Abrindo livro: {pdf_path}...")
    
    extracted_data = []
    
    current_verse = {
        "ref": None,
        "sanskrit": [],
        "translation": [],
        "purport": []
    }
    
    # Estados da Máquina
    state = "SEARCHING" # SEARCHING, SANSKRIT, TRANSLATION, PURPORT

    with pdfplumber.open(pdf_path) as pdf:
        # Vamos ler as primeiras 10 páginas como teste
        for page in pdf.pages[:10]: 
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            
            for line in lines:
                clean_line = line.strip()
                if not clean_line: continue

                # --- 1. DETECTOR DE NOVO VERSO (Ex: "TEXT 1" ou "Verse 1.1.1") ---
                # Ajuste o Regex conforme o padrão do seu PDF
                verse_match = re.search(r'^(TEXT|Verse)\s+(\d+(\.\d+)*)', clean_line, re.IGNORECASE)
                
                if verse_match:
                    # Se já tínhamos um verso sendo processado, salva ele antes de começar o próximo
                    if current_verse["ref"]:
                        print(f"   ✅ Verso {current_verse['ref']} extraído.")
                        # AQUI VOCÊ CHAMARIA O BANCO DE DADOS
                        # save_to_db(current_verse) 
                    
                    # Reseta para o novo verso
                    current_verse = {
                        "ref": verse_match.group(2),
                        "sanskrit": [],
                        "translation": [],
                        "purport": []
                    }
                    state = "SANSKRIT" # Geralmente o sânscrito vem logo depois do número
                    continue

                # --- 2. MÁQUINA DE ESTADOS ---
                
                if state == "SANSKRIT":
                    # Se acharmos a palavra "TRANSLATION", mudamos de estado
                    if "TRANSLATION" in clean_line.upper():
                        state = "TRANSLATION"
                    # Se tem Devanagari ou caracteres especiais de transliteração
                    elif is_sanskrit_or_translit(clean_line):
                        current_verse["sanskrit"].append(clean_line)
                
                elif state == "TRANSLATION":
                    # Se acharmos "PURPORT", mudamos de estado
                    if "PURPORT" in clean_line.upper() or "COMMENTARY" in clean_line.upper():
                        state = "PURPORT"
                    else:
                        # Limpa prefixos como "TRANSLATION:"
                        clean_text = clean_line.replace("TRANSLATION", "").strip()
                        if clean_text: current_verse["translation"].append(clean_text)

                elif state == "PURPORT":
                    # O Purport vai até acharmos o próximo "TEXT X" (que é pego no topo do loop)
                    current_verse["purport"].append(clean_line)

    print("\n🏁 Mineração de PDF concluída.")

def is_sanskrit_or_translit(text):
    # Verifica Devanagari OU diacríticos comuns (ā, ī, ū, ṛ, ṭ, ṇ, ś, etc)
    # Isso é um teste simples, pode ser refinado
    return bool(re.search(r'[\u0900-\u097F]', text)) or bool(re.search(r'[āīūṛṭḍṇśṣṁḥ]', text))

if __name__ == "__main__":
    # COLOQUE O CAMINHO DO SEU PDF AQUI
    mine_pdf_book("bhakti_rasamrta_sindhu_sample.pdf")