const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

class WisdomSearchTest {
    constructor() {
        this.baseUrl = "https://duckduckgo.com/?q=";
    }

    async execute(book, verse) {
        // console.error(`🔍 [NODE] Buscando: ${book} ${verse}`);
        const browser = await puppeteer.launch({
            headless: "new",
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        try {
            const page = await browser.newPage();
            page.setDefaultNavigationTimeout(60000); 
            await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36');

            // 1. Navegação (Padrão)
            const query = encodeURIComponent(`site:wisdomlib.org ${book} ${verse}`);
            await page.goto(`${this.baseUrl}${query}`, { waitUntil: 'domcontentloaded' });
            try { await page.waitForSelector('a', { timeout: 5000 }); } catch(e) {}

            let targetLink = await page.evaluate((v) => {
                const links = Array.from(document.querySelectorAll('a'));
                const exact = links.find(l => l.innerText.includes(v) && l.href.includes('wisdomlib.org'));
                if (exact) return exact.href;
                return links.find(l => l.href.includes('wisdomlib.org/hinduism/book'))?.href;
            }, verse);

            if (!targetLink) throw new Error("Link não encontrado");
            await page.goto(targetLink, { waitUntil: 'domcontentloaded' });

            const isIndex = await page.evaluate(() => document.body.innerText.includes("Contents of this online book"));
            if (isIndex) {
                const verseUrl = await page.evaluate((v) => {
                    const a = Array.from(document.querySelectorAll('a')).find(el => el.innerText.includes(v));
                    return a ? a.href : null;
                }, verse);
                if (verseUrl) await page.goto(verseUrl, { waitUntil: 'domcontentloaded' });
            }

            // 2. EXTRAÇÃO ARRAY (MULTI-TRADUÇÃO)
            const result = await page.evaluate((v_num) => {
                const clean = (text) => text ? text.replace(/\s+/g, ' ').trim() : "";
                const main = document.querySelector('#main') || document.body;
                
                const rawText = main.innerText;
                // Quebra em blocos duplos para isolar parágrafos
                const blocks = rawText.split(/\n\s*\n/).map(b => b.trim()).filter(b => b.length > 3);

                let sanskritText = "";
                let translitText = "";
                let translationsList = []; // AGORA É UMA LISTA
                
                let sanskritIndex = -1;

                // A. Achar Sânscrito
                for (let i = 0; i < blocks.length; i++) {
                    if (/[\u0900-\u097F]/.test(blocks[i]) && !/Resources|Buy|words/i.test(blocks[i])) {
                        sanskritText = clean(blocks[i]);
                        sanskritIndex = i;
                        break; 
                    }
                }

                // B. Achar Transliteração
                if (sanskritIndex !== -1 && (sanskritIndex + 1) < blocks.length) {
                    const nextBlock = blocks[sanskritIndex + 1];
                    if (!/[\u0900-\u097F]/.test(nextBlock) && !/written by|medieval era/i.test(nextBlock)) {
                        translitText = clean(nextBlock);
                    }
                }

                // C. Achar TODAS as Traduções (Loop a partir do texto)
                let startIndex = sanskritIndex + 2; 
                if (startIndex < blocks.length) {
                    for (let i = startIndex; i < blocks.length; i++) {
                        let block = blocks[i];

                        // Filtros de Lixo
                        if (/written by|medieval era|Sanskrit book|English translation of the|Buy now|Resources/i.test(block)) continue;
                        if (/^English translation$/i.test(block) || /^Translation$/i.test(block) || block.length < 20) continue;
                        if (/Commentary|Purport|Source/i.test(block)) break; // Parar se chegar nos comentários

                        // Detecta se é uma tradução válida
                        // WisdomLib costuma usar: "First Translation:", "Second Translation:" ou apenas o texto
                        // Vamos aceitar o bloco se ele passou pelos filtros de lixo
                        let cleanTrans = clean(block.replace(/^(First|Second|Third)?\s*Translation:/i, ''));
                        
                        // Evita duplicatas exatas na lista
                        if (cleanTrans.length > 10 && !translationsList.includes(cleanTrans)) {
                            translationsList.push(cleanTrans);
                        }
                    }
                }

                return {
                    reference: v_num,
                    sanskrit: sanskritText,
                    transliteration: translitText,
                    english_translations: translationsList, // Devolvemos o ARRAY
                    source: window.location.href
                };
            }, verse);

            return result;

        } catch (error) {
            return { error: error.message };
        } finally {
            await browser.close();
        }
    }
}

const args = process.argv.slice(2);
const tester = new WisdomSearchTest();
tester.execute(args[0], args[1]).then(res => {
    process.stdout.write(JSON.stringify(res));
    process.exit(0);
}).catch(() => process.exit(0));