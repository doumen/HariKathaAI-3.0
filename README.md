README.md
SmartAIWrapper v6.7 – Guardião Devocional do HariKathaAI

    “Um cartório devocional que protege a fé, controla custos e garante transparência.”

Índice

    Visão geral [blocked]
    Principais recursos [blocked]
    Requisitos e instalação [blocked]
    Configuração (variáveis de ambiente) [blocked]
    Uso básico (exemplo de chamada) [blocked]
    Arquitetura da base de dados [blocked]
    Política de expurgo (limpeza de logs) [blocked]
    Testes e boas práticas [blocked]
    Contribuição [blocked]
    Licença [blocked]

Visão geral

O SmartAIWrapper é um módulo Python que centraliza a interação com provedores de IA (Gemini, Groq, Whisper, etc.) para o projeto HariKathaAI – um pipeline que transcreve, traduz e comenta volumes altos de áudio e textos sânscritos.

Ele oferece:

    Cache inteligente (hash SHA‑256) – evita custos duplicados.
    Gatekeeper – estima custos antes da chamada e impede despesas acima de um limite configurável.
    Auditoria completa – grava prompt, resposta, tokens, latência, custos estimados e reais, além de um payload JSON.
    Gerenciamento de expurgo – rotina de limpeza automática que mantém o SQLite enxuto sem perder histórico relevante.

Tudo isso com tipagem, logs estruturados e injeção de dependências, facilitando testes e migrações de provedor.
Principais recursos
Recurso	Descrição
Cache por hash	request_hash = SHA‑256(prompt). Respostas já processadas com status_code='SUCCESS' são retornadas imediatamente (custo $0).
Estimativa de tokens	Usa tiktoken (encoding cl100k_base) quando disponível; fallback len(text)//3.
Cálculo de custo	cost = (input/1000) * input_per_1k + (output/1000) * output_per_1k. Tarifas lidas de pricing.json.
Gatekeeper	Bloqueia chamadas que excedem HARI_COST_LIMIT. Em produção registra status_code='COST_BLOCKED'; em desenvolvimento pede confirmação ao usuário.
Auditoria	Tabela ai_audit_logs grava: lecture_id, book_id, job_id, model_name, request_hash, prompt_raw, response_raw, input_tokens, output_tokens, estimated_cost_usd, cost_usd, latency_ms, status_code, payload_json, timestamps.
Exportação CSV	Rotina de expurgo gera backup CSV antes de excluir registros.
Vacuum automático	Após limpeza, o banco passa por VACUUM para liberar espaço físico.
Injeção de dependências	db_path, pricing_path e provider_func podem ser passados ao construtor, facilitando testes unitários.
Logs com emojis	Feedback visual rápido no terminal (⚡, ✅, 🛑).
Requisitos e instalação
Requisito	Versão mínima
Python	3.8
SQLite	embutido no Python
Opcional – tiktoken (para contagem precisa)	pip install tiktoken
Opcional – APScheduler (agendamento interno)	pip install apscheduler
bash

# Clone o repositório
git clone https://github.com/your-org/hari-katha-ai.git
cd hari-katha-ai

# Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Instale dependências
pip install -r requirements.txt   # inclua tiktoken, apscheduler, etc.

# Crie a estrutura de diretórios
mkdir -p database
cp example_pricing.json pricing.json   # ajuste valores conforme contrato

Configuração (variáveis de ambiente)
Variável	Exemplo	Função
HARI_COST_LIMIT	0.10	Limite máximo (USD) para custo estimado por chamada.
HARI_ENV	development ou production	Em production o gatekeeper bloqueia automaticamente; em development solicita confirmação ao usuário.
GEMINI_API_KEY, GROQ_API_KEY, …	(chave da cloud)	Necessárias nas funções de provider real (não incluídas no wrapper).
PYTHONPATH (opcional)	.	Facilita importação de módulos se o projeto estiver em sub‑pastas.

Coloque as variáveis em um arquivo .env e carregue com python-dotenv (opcional).
bash

export HARI_COST_LIMIT=0.15
export HARI_ENV=production

Uso básico (exemplo de chamada)
python

from smart_ai_wrapper import SmartAIWrapper

# Função que realmente chama a API (substitua pelo seu cliente)
def gemini_provider(prompt: str, model: str) -> str:
    # from google.generativeai import configure, GenerativeModel
    # configure(api_key=os.getenv("GEMINI_API_KEY"))
    # return GenerativeModel(model).generate_content(prompt).text
    return "Tradução Sânscrita: Bhakti significa devoção pura."

# Instanciar o wrapper (pode passar caminho customizado para testes)
wrapper = SmartAIWrapper()   # usa DB e pricing padrão

# Chamada real (o wrapper cuida de cache, gatekeeper, auditoria)
response = wrapper.call_ai(
    prompt="Traduza o verso 1.1.1 do Srimad Bhagavatam para o português.",
    model="gemini-1.5-flash",
    lecture_id=42,
    book_id=7,
    provider_func=gemini_provider,
)

print("🗨️ Resposta da IA:", response)

Saída esperada (log simplificado)

2025-12-20 09:09:41,123 INFO  ⚡ [CACHE HIT] Resposta recuperada do banco — custo $0.00
2025-12-20 09:09:42,678 INFO  ✅ [AUDIT] modelo=gemini-1.5-flash status=SUCCESS custo=$0.00452 latência=342ms
🗨️ Resposta da IA: Tradução Sânscrita: Bhakti significa devoção pura.

Arquitetura da base de dados
Schema ai_audit_logs
sql

CREATE TABLE IF NOT EXISTS ai_audit_logs (
    audit_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id          INTEGER,
    book_id             INTEGER,
    job_id              INTEGER,
    model_name          TEXT    NOT NULL,
    request_hash        TEXT    NOT NULL,
    prompt_raw          TEXT    NOT NULL,
    response_raw        TEXT,
    input_tokens        INTEGER NOT NULL,
    output_tokens       INTEGER,
    estimated_cost_usd  REAL    NOT NULL,
    cost_usd            REAL,
    latency_ms          REAL,
    status_code         TEXT    NOT NULL
                               CHECK (status_code IN ('SUCCESS','ERROR','RATE_LIMIT','COST_BLOCKED')),
    payload_json        TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(request_hash, model_name)   -- impede colisões exatas
);

Índices recomendados
sql

CREATE INDEX IF NOT EXISTS idx_audit_hash_model   ON ai_audit_logs(request_hash, model_name);
CREATE INDEX IF NOT EXISTS idx_audit_status      ON ai_audit_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_audit_created DESC ON ai_audit_logs(created_at DESC);

Esses índices garantem buscas rápidas para cache, relatórios financeiros e expurgo.
Política de expurgo (limpeza de logs)

    Objetivo: manter o banco pequeno, evitar degradação de desempenho e ainda garantir a auditoria necessária.

Estratégia padrão (arquivo expurgo_audit.py)
Parâmetro	Valor default	Comentário
--days	90	Registros mais antigos que 90 dias são removidos.
--keep-success	off	Quando ativado, mantêm registros com status_code='SUCCESS' independentemente da idade.
--dry-run	off	Mostra o que seria excluído sem realmente apagar.
Como usar
bash

# Execução semanal via cron (exemplo)
0 3 * * 0 /usr/bin/python3 /caminho/para/expurgo_audit.py --keep-success >> /var/log/expurgo.log 2>&1

O que acontece no script

    Seleção – Busca linhas que atendem ao critério de corte.
    Backup CSV – Exporta as linhas selecionadas para backup/ai_audit_logs_<timestamp>.csv.
    Exclusão – Deleta as linhas selecionadas.
    VACUUM – Recompacta o arquivo SQLite, liberando espaço em disco._

    Importante: O script grava um log detalhado e nunca elimina linhas SUCCESS quando --keep-success está ativo, garantindo que o histórico de custo e latência permaneça disponível para auditoria financeira.

Testes e boas práticas
Testes unitários (exemplo com pytest)
python

import pytest, sqlite3, os
from smart_ai_wrapper import SmartAIWrapper

@pytest.fixture
def db_mem():
    conn = sqlite3.connect(":memory:")
    with open("schema.sql") as f:   # contém o CREATE TABLE acima
        conn.executescript(f.read())
    yield conn
    conn.close()

def test_cache_functionality(db_mem, monkeypatch):
    wrapper = SmartAIWrapper(db_path=":memory:")
    wrapper.db_path = ":memory:"                     # sobrescreve para memória

    # Injeta um provider que devolve sempre a mesma frase
    def stub(p, m): return "Resposta fixa"
    first = wrapper.call_ai("prompt teste", provider_func=stub)
    second = wrapper.call_ai("prompt teste", provider_func=stub)  # deve usar cache

    assert first == "Resposta fixa"
    assert second == "Resposta fixa"

    # Verifica que só houve 1 registro na tabela
    cur = db_mem.execute("SELECT COUNT(*) FROM ai_audit_logs")
    assert cur.fetchone()[0] == 1

Boas práticas recomendadas

    Never hard‑code API keys – use variáveis de ambiente.
    Versionar pricing.json – commit das tarifas (não incluir chaves secretas).
    Executar VACUUM periodicamente (expurgo já faz).
    Monitorar logs – crie um alerta (ex.: via Prometheus) quando o número de chamadas bloqueadas (COST_BLOCKED) subir inesperadamente.

Contribuição

    Fork o repositório.
    Crie uma branch para sua feature (git checkout -b feature/nome).
    Siga o padrão de código (PEP 8, tipagem, docstrings).
    Execute os testes (pytest -q).
    Abra um Pull Request descrevendo claramente a mudança.

    Código de conduta: respeite a cultura Vaishnava e mantenha uma comunicação civilizada nas issues.

Licença

Este projeto está licenciado sob a Apache License 2.0 – veja o arquivo LICENSE para detalhes.
