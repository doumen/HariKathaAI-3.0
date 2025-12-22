const puppeteer = require('puppeteer-extra'); // Mude aqui
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin()); // Ativa o disfarce ninja

const cheerio = require('cheerio');

class WisdomSearchTest {
    constructor() {
        // Mudança tática: Usar busca direta no WisdomLib via Google
        // No constructor
		this.baseUrl = "https://duckduckgo.com/?q=";
    }

    async execute(book, verse) {
        console.error(`🔍 Buscando: ${book} ${verse}`);
        
        const browser = await puppeteer.launch({ 
            headless: "new", // Pode mudar para false se quiser ver o navegador abrindo
            args: ['--no-sandbox'] 
        });
        
        const page = await browser.newPage();

		try {
            const query = encodeURIComponent(`site:wisdomlib.org ${book} ${verse}`);
            await page.goto(`${this.baseUrl}${query}`, { waitUntil: 'networkidle2' });

            // DuckDuckGo usa classes como '.results' ou o ID 'links'
            // Esperamos carregar qualquer link para garantir que a busca terminou
            await page.waitForSelector('a', { timeout: 10000 });

            const firstLink = await page.evaluate(() => {
                // Selecionamos todos os links da página
                const links = Array.from(document.querySelectorAll('a'));
                // Procuramos o primeiro que aponte para o livro no WisdomLib
                const wisdomLink = links.find(l => 
                    l.href.includes('wisdomlib.org/hinduism/book') || 
                    l.href.includes('wisdomlib.org/vaishnavism/book')
                );
                return wisdomLink ? wisdomLink.href : null;
            });

            if (!firstLink) {
                await page.screenshot({ path: 'duckduckgo_debug.png' });
                throw new Error("Link não encontrado no DuckDuckGo.");
            }

            console.error(`🔗 Sucesso: ${firstLink}`);
            
            // Navega para o WisdomLib
            await page.goto(firstLink, { waitUntil: 'domcontentloaded' });
            
            const html = await page.content();
            const $ = cheerio.load(html);

            // Extração dos dados baseada na estrutura do WisdomLib que você enviou
            return {
                referencia: $('h1').text().trim() || `${book} ${verse}`,
                sânscrito: $('.sanskrit').first().text().trim(),
                transliteracao: $('.unicode').first().text().trim(),
                fonte: firstLink
            };        
        } catch (error) {
            console.error("❌ Erro:", error.message);
            return null;
        } finally {
            await browser.close();
        }
    }
}

// ... (resto do script igual ao anterior)
// Execução Final
const args = process.argv.slice(2);
const book = args[0] || "Bhakti-rasamrta-sindhu";
const verse = args[1] || "1.1.1";

const tester = new WisdomSearchTest();

tester.execute(book, verse).then(result => {
    if (result && result.sânscrito) {
        // Único lugar onde o JSON é escrito no stdout
        process.stdout.write(JSON.stringify(result));
    } else {
        process.exit(1);
    }
    process.exit(0);
}).catch(err => {
    console.error("Erro fatal:", err);
    process.exit(1);
});