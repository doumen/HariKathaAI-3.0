/**
 * web_scraper.js
 * * O "Colhedor" oficial do HariKathaAI.
 * * Funcionalidades:
 * 1. Tenta obter URL direta do banco (Mapeada pelo Cartographer).
 * 2. Se falhar, busca no DuckDuckGo (site:wisdomlib.org).
 * 3. Extrai Sânscrito, Transliteração e Traduções Múltiplas.
 * 4. Retorna JSON para o Python.
 */

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

puppeteer.use(StealthPlugin());

// Configuração do Caminho do Banco de Dados
const DB_PATH = path.resolve(__dirname, '../../database/harikatha.db');

class WisdomScraper {
    constructor() {
        this.db = new sqlite3.Database(DB_PATH);
    }

    /**
     * Busca a URL mapeada no banco de dados para evitar busca lenta.
     */
    async getDirectUrl(bookAcronym, verseRef) {
        return new Promise((resolve, reject) => {
            const sql = `
                SELECT m.direct_url 
                FROM wisdom_url_map m
                JOIN library_books b ON m.book_id = b.id
                WHERE b.acronym = ? AND m.verse_ref = ?
            `;
            this.db.get(sql, [bookAcronym, verseRef], (err, row) => {
                if (err) reject(err);
                resolve(row ? row.direct_url : null);
            });
        });
    }

    async execute(book, verse) {
        const browser = await puppeteer.launch({
            headless: "new",
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        try {
            const page = await browser.newPage();
            // User-Agent para evitar bloqueios
            await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36');

            // --- ESTRATÉGIA 1: CARTÓGRAFO (BANCO DE DADOS) ---
            let targetUrl = await this.getDirectUrl(book, verse);
            let strategy = "DATABASE_MAP";

            // --- ESTRATÉGIA 2: BUSCA (FALLBACK) ---
            if (!targetUrl) {
                // console.error(`⚠️ URL não mapeada para ${book} ${verse}. Iniciando busca web...`);
                strategy = "WEB_SEARCH";
                const query = encodeURIComponent(`site:wisdomlib.org ${book} ${verse}`);
                await page.goto(`https://duckduckgo.com/?q=${query}`, { waitUntil: 'domcontentloaded' });
                
                try { await page.waitForSelector('a', { timeout: 5000 }); } catch(e) {}

                targetUrl = await page.evaluate((v) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    // Tenta achar link exato
                    const exact = links.find(l => l.innerText.includes(v) && l.href.includes('wisdomlib.org'));
                    if (exact) return exact.href;
                    // Se não, pega o primeiro do wisdomlib
                    return links.find(l => l.href.includes('wisdomlib.org/hinduism/book'))?.href;
                }, verse);
            }

            if (!targetUrl) throw new Error("URL não encontrada nem no mapa, nem na busca.");

            // Navega para a página do verso
            await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });

            // Verifica se caiu num Índice em vez do Verso (comum no WisdomLib)
            const isIndex = await page.evaluate(() => document.body.innerText.includes("Contents of this online book"));
            if (isIndex) {
                const verseUrl = await page.evaluate((v) => {
                    const a = Array.from(document.querySelectorAll('a')).find(el => el.innerText.includes(v));
                    return a ? a.href : null;
                }, verse);
                if (verseUrl) await page.goto(verseUrl, { waitUntil: 'domcontentloaded' });
            }

            // --- ESTRATÉGIA DE EXTRAÇÃO (SEMÂNTICA) ---
            const result = await page.evaluate((v_num) => {
                const clean = (text) => text ? text.replace(/\s+/g, ' ').trim() : "";
                
                // Seleciona a área principal de conteúdo (varia conforme o layout do wisdomlib)
                const main = document.querySelector('#content') || document.querySelector('#main') || document.body;
                const rawText = main.innerText;
                
                // Divide em blocos por quebra de linha dupla (parágrafos)
                const blocks = rawText.split(/\n\s*\n/).map(b => b.trim()).filter(b => b.length > 3);

                let sanskritText = "";
                let translitText = "";
                let translationsList = [];
                let commentariesList = [];
                
                let sanskritIndex = -1;

                // 1. Detectar Sânscrito (Devanagari Unicode Range)
                for (let i = 0; i < blocks.length; i++) {
                    if (/[\u0900-\u097F]/.test(blocks[i]) && !/Resources|Buy|words/i.test(blocks[i])) {
                        sanskritText = clean(blocks[i]);
                        sanskritIndex = i;
                        break; 
                    }
                }

                // 2. Detectar Transliteração (Geralmente logo após o Sânscrito)
                if (sanskritIndex !== -1 && (sanskritIndex + 1) < blocks.length) {
                    const nextBlock = blocks[sanskritIndex + 1];
                    // Se não tiver Devanagari e não for texto administrativo
                    if (!/[\u0900-\u097F]/.test(nextBlock) && !/written by|medieval era/i.test(nextBlock)) {
                        translitText = clean(nextBlock);
                    }
                }

                // 3. Detectar Traduções e Comentários
                let startIndex = sanskritIndex > -1 ? sanskritIndex + 2 : 0;
                let mode = 'TRANSLATION'; // Começa procurando tradução

                for (let i = startIndex; i < blocks.length; i++) {
                    let block = blocks[i];

                    // Filtros de Lixo do Site
                    if (/written by|medieval era|Sanskrit book|English translation of the|Buy now|Resources/i.test(block)) continue;
                    if (/^English translation$/i.test(block) || /^Translation$/i.test(block)) continue;
                    if (block.length < 10) continue;

                    // Gatilho: Mudança para Comentário
                    if (/Commentary|Purport|Meaning/i.test(block)) {
                        mode = 'COMMENTARY';
                        continue;
                    }

                    // Limpeza de prefixos comuns
                    let cleanBlock = clean(block.replace(/^(First|Second|Third)?\s*Translation:/i, ''));

                    if (mode === 'TRANSLATION') {
                        if (!translationsList.includes(cleanBlock)) {
                            translationsList.push(cleanBlock);
                        }
                    } else if (mode === 'COMMENTARY') {
                         if (!commentariesList.includes(cleanBlock)) {
                            commentariesList.push(cleanBlock);
                        }
                    }
                }

                return {
                    reference: v_num,
                    sanskrit: sanskritText,
                    transliteration: translitText,
                    english_translations: translationsList,
                    english_commentaries: commentariesList,
                    source_url: window.location.href
                };
            }, verse);

            // Adiciona metadados da execução
            result.strategy_used = strategy;
            return result;

        } catch (error) {
            return { error: error.message };
        } finally {
            await browser.close();
            this.db.close();
        }
    }
}

// --- EXECUÇÃO VIA LINHA DE COMANDO (PARA O PYTHON CHAMAR) ---
// Exemplo: node src/ingestion/web_scraper.js BRS 1.1.1
const args = process.argv.slice(2);
if (args.length >= 2) {
    const scraper = new WisdomScraper();
    scraper.execute(args[0], args[1]).then(res => {
        // Imprime JSON no