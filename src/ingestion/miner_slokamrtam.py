#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
miner_slokamrtam.py (Versão V23.0 - The Final Polish)

Correções Finais:
1. Unglue Heavy: Resolve 'Iofferpraṇāma...' injetando espaços em blobs gigantes.
2. W2W Estrutural: Detecta W2W por ';...—' mesmo que o texto esteja quebrado.
3. Ref Splitter: Remove referências teimosas da raiz.
"""

import os
import re
import sys
import sqlite3
import logging
import pdfplumber
from typing import List, Tuple

# --- Configurações ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from src.intelligence.librarian_storage import (
    _ensure_book_id,
    _ensure_index_id,
    _upsert_root_text,
    _upsert_translation,
    _upsert_commentary
)

DB_PATH  = os.path.join(PROJECT_ROOT, "database", "harikatha.db")
PDF_PATH = "Sri Slokamrtam Cinmaya v1.0.qxp - Sri_Slokamritam.pdf"

logger = logging.getLogger("SlokamrtamMiner")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

# --- 1. Ferramentas de Texto ---

def fix_exploded_words(text: str) -> str:
    """Junta letras explodidas (b r o t h e r)."""
    def replacement(match):
        return match.group(0).replace(" ", "")
    # Evita juntar "a I" ou "I a"
    pattern = r'\b(?<!I )([a-z])\s([a-z])\s([a-z])(\s([a-z]))*\b'
    text = re.sub(pattern, replacement, text)
    return text

def unglue_heavy(text: str) -> str:
    """
    Aplica força bruta para separar blobs como 'Iofferpraṇāmatothelotus'.
    Usa lista de palavras-chave seguras.
    """
    # 1. Separa o "I" inicial
    text = re.sub(r'^I([a-z])', r'I \1', text)
    text = re.sub(r'([“"\'\s])I([a-z])', r'\1I \2', text)

    # 2. Lista de partículas e palavras comuns na tradução
    keywords = [
        "the", "of", "to", "and", "is", "in", "that", "with", "are", 
        "my", "your", "his", "her", "lotus", "feet", "offer", "respectful", 
        "obeisances", "unto", "spiritual", "master"
    ]
    
    for k in keywords:
        # Insere espaço antes da palavra se ela estiver grudada em letra minúscula
        # (?<=[a-z]) = lookbehind (se tiver letra antes)
        # (?=[a-z]) = lookahead (se tiver letra depois)
        
        # CUIDADO: "to" pode quebrar "stotra". "is" pode quebrar "krisna".
        # Só aplicamos se a palavra chave for longa ou muito segura
        if len(k) > 2 or k in ["of"]:
             text = re.sub(f'(?<=[a-z]){k}', f' {k}', text)
             text = re.sub(f'{k}(?=[a-z])', f'{k} ', text)
        elif k in ["to", "is"]: 
            # Para curtas, exigimos contexto mais específico do inglês desse livro
            if "tothelotus" in text: text = text.replace("tothelotus", "to the lotus")
            if "inthe" in text: text = text.replace("inthe", "in the")
            
    # Limpa espaços duplos
    return re.sub(r'\s+', ' ', text).strip()

def unglue_boundaries(text: str) -> str:
    """Separa palavras coladas em transições simples."""
    text = re.sub(r'([a-z])([A-ZÇŚṢṚ])', r'\1 \2', text)
    text = re.sub(r';([a-zA-Z])', r'; \1', text)
    
    safe_splits = {
        "ofthe": "of the", "tothe": "to the", "inthe": "in the",
        "byme": "by me", "forme": "for me", "ofmy": "of my", "tomy": "to my",
        "offermy": "offer my", "lotusfeet": "lotus feet", "thelotus": "the lotus",
        "respectfulobeisances": "respectful obeisances", "iscalled": "is called",
        "offerpranama": "offer pranama", "feetof": "feet of", "unto": "unto"
    }
    words = text.split()
    fixed_words = []
    for w in words:
        clean_w = w.strip('.,;“"').lower()
        if clean_w in safe_splits:
            fixed = safe_splits[clean_w]
            if w.endswith(';'): fixed += ';'
            elif w.endswith('.'): fixed += '.'
            fixed_words.append(fixed)
        else:
            fixed_words.append(w)
    return " ".join(fixed_words)

def normalize_text(text: str) -> str:
    if not text: return ""
    
    text = fix_exploded_words(text)
    text = unglue_boundaries(text)

    # DETECTOR DE BLOB GIGANTE (Para SLK_0.1)
    # Se a linha for longa e tiver menos de 3 espaços
    if len(text) > 40 and text.count(" ") < 3:
        text = unglue_heavy(text)

    text = re.sub(r'[—–−]', '—', text) 
    text = re.sub(r'\s*—\s*', ' — ', text) 
    
    if '—' in text:
        parts = text.split('—', 1)
        left = parts[0].strip()
        right = parts[1].strip()
        right = unglue_boundaries(right) # Aplica limpeza no inglês
        text = f"{left} — {right}"
    
    replacements = {
        'ä': 'ā', 'é': 'ī',  'ü': 'ū',
        'å': 'ṛ', 'è': 'ṝ',  'ì': 'ṅ', 'ï': 'ñ',
        'ö': 'ṭ', 'ò': 'ḍ',  'ë': 'ṇ',
        'ç': 'ś', 'ñ': 'ṣ',  'à': 'ṁ', 'ù': 'ḥ',
        'â': 't', 'î': 'i',  'û': 'u',
        'S': 'S', 
    }
    clean = text
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    
    clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)
    clean = re.sub(r'([a-z])(\.)([A-Z])', r'\1\2 \3', clean)
    clean = re.sub(r'(vol\.)(\d)', r'\1 \2', clean, flags=re.IGNORECASE)
    
    return clean.strip()

def is_noise(line: str) -> bool:
    l = line.strip().lower()
    if len(l) < 2: return True 
    if any(tok in l for tok in ["page", "index", "contents", "slokamrtam", "chapter"]): return True
    return False

# --- 2. Classificadores ---

def has_diacritics(line: str) -> bool:
    return any(c in line for c in "āīūṛṝṅñṭḍṇśṣṁḥ")

def split_ref_from_root(text: str) -> Tuple[str, str]:
    """Corta referências grudadas no final da Raiz."""
    patterns = [
        r'(\([A-Z]+\s*p\.\s*\d+[\.\d]*\))$',       # (SGG p. 152)
        r'(\(SGG.*\))$',                            # Genérico SGG
        r'(\([A-Z]{2,}\s*[\d\.]+\s*(?:pt)?.*\))$',  # (BR 8.5 pt...)
        r'(\d+\.[A-Z]\.\d+(?:\([a-z]\))?)$',        # 12.F.23(b)
        r'(\(.*\)\s*siddha.*)$',                    # Matha siddha
        r'(\[.*philosophy\).+\])$'                  # Editorial note
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            ref = match.group(1)
            root = text.replace(ref, "").strip()
            if len(root) < 3: root = ""
            return root, ref
    return text, None

def is_reference_line(line: str) -> bool:
    clean = line.strip()
    if len(clean) > 120: return False 
    
    if "(SGG" in clean or "(BR" in clean: return True
    
    markers = [
        r'\bSB\b', r'\bCC\b', r'\bBg\b', r'\bVeda\b', r'\bPurana\b', 
        r'\bUpanisad\b', r'\bGita\b', r'\bStava\b', r'\bVidagdha\b', 
        r'\bVol\.', r'\bSermons\b', r'\bNectar\b', 
        r'\bCandramrta\b', r'\bKarnamrta\b'
    ]
    has_marker = any(re.search(pat, clean, re.IGNORECASE) for pat in markers)
    has_digit = any(c.isdigit() for c in clean)
    
    if has_marker and (has_digit or '/' in clean): return True
    if ("Thakura" in clean or "Gosvami" in clean) and len(clean) < 70: return True
    return False

def contains_english_words(line: str) -> bool:
    english_stops = {
        'the', 'of', 'to', 'and', 'is', 'in', 'that', 'with', 'are', 'my', 'your', 'his', 'her',
        'me', 'us', 'we', 'but', 'for', 'by', 'from', 'this', 'have', 'not', 'be', 'so', 'one',
        'mercy', 'heart', 'soul', 'feet', 'lotus', 'love', 'holy', 'name', 'sins', 'fallen', 'life',
        'giver', 'desire', 'please', 'respectful', 'obeisances', 'spiritual', 'master'
    }
    words = set(re.findall(r'\w+', line.lower()))
    return len(words.intersection(english_stops)) >= 1

def is_english_start(line: str, raw_line: str) -> bool:
    if line.startswith('“') or line.startswith('"'): return True
    starters = ["I offer", "All glories", "O Lord", "He who", "Although", "My dear", "I am", "You are", "As a", "Strictly", "The", "This", "That", "Do not"]
    if any(line.startswith(s) for s in starters): return True

    if has_diacritics(line) and not contains_english_words(line): return False
    
    has_indent = raw_line.startswith('  ') or raw_line.startswith('\t')
    if has_indent and contains_english_words(line): return True
    
    words = re.findall(r'\w+', line.lower())
    if not words: return False
    match_count = sum(1 for w in words if w in {'the', 'of', 'to', 'and', 'is', 'in', 'my', 'your'})
    if len(words) > 3 and (match_count / len(words) > 0.15): return True

    return False

def is_title_line(line: str) -> bool:
    l = line.strip()
    if len(l) > 70 or l.endswith('.'): return False
    keywords = ["Pranama", "Tattva", "Vandana", "Lila", "Astaka", "Gita", "Stotram", "Samasta", "Vijñapti", "Kirtana", "Rasa-tattva", "Deva!", "Bhavantam"]
    if any(k in l for k in keywords): return True
    if (l.startswith("Çré") or l.startswith("Śrī")) and len(l) < 50: return True
    return False

def clean_root_line(line: str) -> str:
    return re.sub(r'\s*\(\d+\)$', '', line).strip()

# --- 3. Processador ---

def process_verse_block(lines: List[str]) -> dict:
    sanskrit = []
    reference = []
    w2w = []
    translation = []
    state = 0 

    for raw in lines:
        clean = normalize_text(raw)
        if not clean: continue
        
        is_ref = is_reference_line(clean)
        
        # W2W Estrutural: Travessão E (Inglês OU Ponto-e-vírgula)
        # Isso resolve o SLK_22.20 e SLK_11.40 que estavam indo para Raiz
        has_dash = '—' in clean or (clean.count('-') > 0 and ";" in clean)
        has_semicolon = ";" in clean
        is_w2w = has_dash and (contains_english_words(clean) or has_semicolon)
        
        if is_ref: is_w2w = False
        
        is_trans = is_english_start(clean, raw)
        if is_w2w: is_trans = False

        if state == 0: # Sânscrito
            if is_trans:
                state = 2
                translation.append(clean)
            elif is_ref:
                state = 1
                reference.append(clean)
            elif is_w2w:
                state = 1
                w2w.append(clean)
            else:
                root_part, ref_part = split_ref_from_root(clean_root_line(clean))
                if root_part: sanskrit.append(root_part)
                if ref_part: reference.append(ref_part)
                
        elif state == 1: # Ref/W2W
            if is_trans:
                state = 2
                translation.append(clean)
            elif is_w2w:
                w2w.append(clean)
            elif is_ref:
                reference.append(clean)
            else:
                if has_diacritics(clean) and not contains_english_words(clean):
                    sanskrit.append(clean_root_line(clean))
                else:
                    state = 2
                    translation.append(clean)
                
        elif state == 2: # Tradução
            if has_diacritics(clean) and not contains_english_words(clean) and '(' in clean:
                 sanskrit.append(clean_root_line(clean))
            elif is_ref:
                 reference.append(clean)
            else:
                translation.append(clean)

    while translation and is_title_line(translation[-1]):
        translation.pop()

    full_trans = "\n".join(translation)
    commentary = None
    note_match = re.search(r'\[(Editorial\s*note:.*?)\]', full_trans, re.DOTALL | re.IGNORECASE)
    if note_match:
        commentary = note_match.group(1).strip()
        full_trans = full_trans.replace(note_match.group(0), "").strip()
        
    final_w2w = "\n".join(w2w) if w2w else None

    return {
        "root": "\n".join(sanskrit),
        "ref": " ".join(reference),
        "w2w": final_w2w,
        "body": full_trans.strip(),
        "commentary": commentary
    }

# --- 4. Extração ---

def extract_columns(page) -> List[str]:
    w, h = page.width, page.height
    settings = {"x_tolerance": 3, "y_tolerance": 3} 
    top, bottom = h * 0.06, h * 0.94
    l_box = (0, top, w * 0.50, bottom)
    r_box = (w * 0.50, top, w, bottom)
    l_txt = page.within_bbox(l_box).extract_text(**settings) or ""
    r_txt = page.within_bbox(r_box).extract_text(**settings) or ""
    return (l_txt + "\n" + r_txt).split('\n')

# --- 5. Persistência ---

def save_to_db(conn: sqlite3.Connection, ref: str, lines: List[str], chapter: str):
    if not ref or not lines: return
    try:
        data = process_verse_block(lines)
        book_id = _ensure_book_id(conn, "SLK")
        canonical_id = f"SLK_{ref}"
        index_id = _ensure_index_id(conn, book_id, canonical_id, ref)
        
        if data["root"]:
            _upsert_root_text(conn, index_id, None, data["root"])
            
        if data["body"] or data["ref"] or data["commentary"] or data["w2w"]:
            _upsert_translation(
                conn, index_id, "en", "Slokamrtam Book",
                text_body=data["body"],
                word_for_word=data["w2w"], 
                source_ref=data["ref"],
                commentary=data["commentary"]
            )

        if chapter and len(chapter) > 3 and ":" not in chapter:
            conn.execute("INSERT OR IGNORE INTO theological_concepts (term, category) VALUES (?, 'Tattva')", (chapter.lower(),))
            res = conn.execute("SELECT id FROM theological_concepts WHERE term = ?", (chapter.lower(),)).fetchone()
            if res:
                conn.execute("INSERT OR REPLACE INTO content_tags (concept_id, library_index_id, relevance_score) VALUES (?, ?, 2.0)", (res[0], index_id))

        status = "Root✅" if data["root"] else "Root❌"

    except Exception as e:
        logger.error(f"❌ Erro {ref}: {e}")

# --- 6. Main ---

def mine_slokamrtam():
    logger.info(f"🔨 Mineração V23.0 (Final Polish): {PDF_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO library_books (acronym, book_title) VALUES ('SLK', 'Śrī Ślokāmṛtam')")
    conn.commit()
    
    verse_num_regex = re.compile(r"^\s*(\d+\.\d+)\s*$")
    chapter_regex = re.compile(r"^(Chapter|SAMBANDHA|ABHIDHEYA|PRAYOJANA)\s*(\d*)\s*[-–]?\s*(.*)", re.IGNORECASE)

    curr_ref = None
    curr_lines = []
    curr_chapter = "Introduction"

    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages[8:], start=9):
            lines = extract_columns(page)
            for raw in lines:
                clean = raw.strip()
                if not clean or is_noise(clean): continue
                
                chap_match = chapter_regex.search(clean)
                if chap_match:
                    part3 = chap_match.group(3).strip()
                    new_chap = part3 if part3 else clean
                    if len(new_chap) > 3 and ":" not in new_chap:
                        if curr_ref:
                            save_to_db(conn, curr_ref, curr_lines, curr_chapter)
                            curr_ref, curr_lines = None, []
                        curr_chapter = new_chap
                        logger.info(f"📂 Tópico: {curr_chapter}")
                    continue

                verse_match = verse_num_regex.match(clean)
                if verse_match:
                    if curr_ref:
                        save_to_db(conn, curr_ref, curr_lines, curr_chapter)
                    
                    curr_ref = verse_match.group(1)
                    curr_lines = []
                    continue
                
                if curr_ref:
                    curr_lines.append(raw)

            if curr_ref:
                save_to_db(conn, curr_ref, curr_lines, curr_chapter)
            
    conn.commit()
    conn.close()
    logger.info("🏁 Processo Concluído.")

if __name__ == "__main__":
    if os.path.exists(PDF_PATH):
        mine_slokamrtam()
    else:
        logger.error("PDF não encontrado.")