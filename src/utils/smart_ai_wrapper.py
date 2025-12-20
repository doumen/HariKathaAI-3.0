#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SmartAIWrapper v6.7 – Guardião Devocional do HariKathaAI

Recursos principais:
- Cache inteligente (SHA‑256) com recuperação rápida.
- Estimativa e cálculo preciso de custo (input + output tokens).
- Gatekeeper configurável via variáveis de ambiente.
- Auditoria completa (prompt, resposta, tokens, latência, custo estimado, custo real, payload JSON).
- Suporte opcional a tiktoken para contagem exata de tokens.
- Injeção de dependências (db_path, pricing_path, provider_func) para testes.
- Rotina de expurgo (arquivo separado) para limpeza automática do SQLite.
"""

import os
import json
import hashlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional, Dict, Any

# ----------------------------------------------------------------------
# Configurações globais
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # ajuste se o script mudar de local
DEFAULT_DB = BASE_DIR / "database" / "harikatha.db"
DEFAULT_PRICING = BASE_DIR / "pricing.json"

logger = logging.getLogger("SmartAIWrapper")
logger.setLevel(logging.INFO)

# ----------------------------------------------------------------------
class SmartAIWrapper:
    """
    Wrapper centralizado para chamadas a modelos de IA com:
    - Cache via SHA‑256
    - Gatekeeper de custo
    - Auditoria detalhada
    - Possibilidade de injetar função real de chamada (provider_func)
    """

    # ------------------------------------------------------------------
    def __init__(self,
                 db_path: Optional[Path] = None,
                 pricing_path: Optional[Path] = None) -> None:
        """
        Parameters
        ----------
        db_path : Path | None
            Caminho opcional para o SQLite (padrão = DEFAULT_DB). Útil em testes.
        pricing_path : Path | None
            Caminho opcional para o arquivo pricing.json (padrão = DEFAULT_PRICING).
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.pricing_path = Path(pricing_path) if pricing_path else DEFAULT_PRICING

        self._load_pricing()

        # Configurações de ambiente
        self.cost_limit = float(os.getenv("HARI_COST_LIMIT", "0.10"))   # USD
        self.env = os.getenv("HARI_ENV", "development")               # development | production

    # ------------------------------------------------------------------
    def _load_pricing(self) -> None:
        """Carrega tarifas de pricing.json ou usa fallback seguro."""
        if not self.pricing_path.is_file():
            logger.warning(
                f"⚠️ pricing.json não encontrado em {self.pricing_path}. "
                "Usando tarifas padrão."
            )
            self.pricing = {
                "default": {"input_per_1k": 0.00015, "output_per_1k": 0.00060}
            }
        else:
            with open(self.pricing_path, encoding="utf-8") as f:
                self.pricing = json.load(f)

    # ------------------------------------------------------------------
    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """Retorna hash SHA‑256 do prompt (identificador único)."""
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    @staticmethod
    def _count_tokens(text: str, model: str = "default") -> int:
        """
        Conta tokens usando tiktoken quando disponível.
        Fallback: 1 token ≈ 3 caracteres (conservador).
        """
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")   # funciona para GPT‑4/Gemini‑Flash etc.
            return len(enc.encode(text))
        except Exception:
            # Heurística segura
            return max(1, len(text) // 3)

    # ------------------------------------------------------------------
    def _calculate_cost(self,
                        model: str,
                        input_tokens: int,
                        output_tokens: int) -> float:
        """Cálculo do custo em USD (input + output)."""
        rates = self.pricing.get(model, self.pricing.get("default", {}))
        if not rates:
            return 0.0
        return (input_tokens / 1000) * rates.get("input_per_1k", 0) + \
               (output_tokens / 1000) * rates.get("output_per_1k", 0)

    # ------------------------------------------------------------------
    def _check_cache(self, request_hash: str, model: str) -> Optional[str]:
        """Retorna resposta cacheada (mais recente) ou None."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    """
                    SELECT response_raw FROM ai_audit_logs
                    WHERE request_hash = ? AND model_name = ?
                      AND status_code = 'SUCCESS'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (request_hash, model),
                )
                row = cur.fetchone()
                return row[0] if row else None
        except sqlite3.OperationalError:
            # Tabela pode ainda não existir – ignora cache
            return None

    # ------------------------------------------------------------------
    def _register_audit(self, data: Dict[str, Any]) -> None:
        """
        Insere registro completo na tabela ai_audit_logs.

        Campos esperados em ``data``:
        lecture_id, book_id, job_id, model_name, request_hash,
        prompt_raw, response_raw, input_tokens, output_tokens,
        estimated_cost_usd, cost_usd, latency_ms, status_code,
        payload_json
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO ai_audit_logs (
                        lecture_id, book_id, job_id, model_name, request_hash,
                        prompt_raw, response_raw,
                        input_tokens, output_tokens,
                        estimated_cost_usd, cost_usd,
                        latency_ms, status_code, payload_json,
                        created_at, updated_at
                    ) VALUES (
                        :lecture_id, :book_id, :job_id, :model_name, :request_hash,
                        :prompt_raw, :response_raw,
                        :input_tokens, :output_tokens,
                        :estimated_cost_usd, :cost_usd,
                        :latency_ms, :status_code, :payload_json,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """,
                    data,
                )
            logger.info(
                f"✅ [AUDIT] modelo={data['model_name']} "
                f"status={data['status_code']} custo=${data['cost_usd']:.5f} "
                f"lat={data['latency_ms']}ms"
            )
        except Exception as exc:
            logger.error(f"❌ Falha ao gravar auditoria: {exc}")

    # ------------------------------------------------------------------
    def call_ai(self,
                prompt: str,
                model: str = "gemini-1.5-flash",
                lecture_id: Optional[int] = None,
                book_id: Optional[int] = None,
                job_id: Optional[int] = None,
                force: bool = False,
                provider_func: Optional[Callable[[str, str], str]] = None) -> Optional[str]:
        """
        Executa a chamada ao modelo de IA com:
        1️⃣ Verificação de cache (se ``force`` = False).
        2️⃣ Estimativa de custo e gatekeeper.
        3️⃣ Execução real (via ``provider_func`` ou simulação).
        4️⃣ Registro de auditoria completo.

        Retorna a resposta da IA quando ``status_code == 'SUCCESS'``,
        ou ``None`` em caso de bloqueio ou erro.
        """
        request_hash = self._hash_prompt(prompt)

        # -------------------- 1️⃣ CACHE --------------------
        if not force:
            cached = self._check_cache(request_hash, model)
            if cached:
                logger.info("⚡ [CACHE HIT] Resposta recuperada – custo $0.00")
                return cached

        # -------------------- 2️⃣ GATEKEEPER --------------------
        input_tokens = self._count_tokens(prompt, model)
        # Chute conservador para saída: max(1000, input/2)
        est_output_tokens = max(1000, input_tokens // 2)
        est_cost = self._calculate_cost(model, input_tokens, est_output_tokens)

        logger.info(
            f"[GATEKEEPER] modelo={model} "
            f"in={input_tokens} out≈{est_output_tokens} "
            f"custo_estimado=${est_cost:.5f}"
        )

        if est_cost > self.cost_limit:
            msg = f"Custo estimado ${est_cost:.5f} > limite ${self.cost_limit:.2f}"
            if self.env == "production":
                logger.error(f"🛑 [BLOCKED] {msg}")
                self._register_audit({
                    "lecture_id": lecture_id,
                    "book_id": book_id,
                    "job_id": job_id,
                    "model_name": model,
                    "request_hash": request_hash,
                    "prompt_raw": prompt,
                    "response_raw": "",
                    "input_tokens": input_tokens,
                    "output_tokens": 0,
                    "estimated_cost_usd": est_cost,
                    "cost_usd": 0.0,
                    "latency_ms": 0,
                    "status_code": "COST_BLOCKED",
                    "payload_json": json.dumps({"prompt": prompt, "model": model}),
                })
                return None
            else:
                confirm = input(f"⚠️ {msg}. Prosseguir? (y/n): ")
                if confirm.lower() not in {"y", "yes", "s", "sim"}:
                    logger.info("❌ Chamada abortada pelo usuário.")
                    return None

        # -------------------- 3️⃣ EXECUÇÃO --------------------
        start = time.perf_counter()
        status = "SUCCESS"
        response = ""
        error_msg = ""

        try:
            if provider_func:
                response = provider_func(prompt, model)   # chamada real
            else:
                # Simulação para desenvolvimento / teste
                time.sleep(0.5)
                response = f"[SIMULAÇÃO] Resposta para: {prompt[:30]}..."
        except Exception as exc:
            status = "ERROR"
            error_msg = str(exc)
            response = error_msg
            logger.error(f"❌ Erro ao chamar IA: {exc}")

        latency_ms = int((time.perf_counter() - start) * 1000)

        # -------------------- 4️⃣ CÁLCULO FINAL --------------------
        output_tokens = self._count_tokens(response, model) if status == "SUCCESS" else 0
        real_cost = (
            self._calculate_cost(model, input_tokens, output_tokens)
            if status == "SUCCESS"
            else 0.0
        )

        # -------------------- 5️⃣ AUDITORIA --------------------
        self._register_audit({
            "lecture_id": lecture_id,
            "book_id": book_id,
            "job_id": job_id,
            "model_name": model,
            "request_hash": request_hash,
            "prompt_raw": prompt,                 # texto integral
            "response_raw": response,              # texto integral
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": est_cost,
            "cost_usd": real_cost,
            "latency_ms": latency_ms,
            "status_code": status,
            "payload_json": json.dumps({"prompt": prompt, "model": model}),
        })

        return response if status == "SUCCESS" else None


# ----------------------------------------------------------------------
# Exemplo de uso (executável direto)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    def gemini_provider(prompt: str, model: str) -> str:
        """
        Substitua por chamada real da API Gemini:
        ```python
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return genai.GenerativeModel(model).generate_content(prompt).text
        ```
        """
        return "Tradução Sânscrita: Bhakti significa amor puro."

    wrapper = SmartAIWrapper()   # usa DB e pricing padrão

    print("\n--- Teste de chamada ---")
    resposta = wrapper.call_ai(
        prompt="Traduza o verso 1.1.1 do Srimad Bhagavatam para o português.",
        model="gemini-1.5-flash",
        lecture_id=1,
        book_id=1,
        provider_func=gemini_provider,
    )
    print(f"Resultado: {resposta}")
