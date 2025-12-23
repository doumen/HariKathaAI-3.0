# Log de Ingestão: Śrī Ślokāmṛtam

**Data:** 23/12/2025
**Status:** Sucesso (Gold Standard)
**Fonte:** Sri Slokamrtam Cinmaya v1.0.qxp - Sri_Slokamritam.pdf

## 📜 Ordem de Execução (Pipeline)

Para reproduzir a carga deste livro no banco de dados, execute os scripts na seguinte ordem estrita:

### 1. Mineração Principal (V23.0)
* **Script:** `src/ingestion/miner_slokamrtam.py`
* **Função:** Lê o PDF, aplica heurística de espaçamento (x_tolerance=3) e limpeza de "blobs" de texto (Inglês grudado).
* **Resultado:** Insere ~912 versos brutos no banco.

### 2. Correção Manual do Verso 1.0
* **Script:** `src/scripts/fix_slk_1_0.py`
* **Função:** Reconstrói o verso SLK_1.0 que foi fragmentado devido à formatação complexa da página. Insere dados hardcoded extraídos manualmente.

### 3. Patch Manual (Imagens)
* **Script:** `src/scripts/final_patch.py`
* **Função:** Corrige 10 casos de borda (referências grudadas, texto corrompido) baseando-se em verificação visual das imagens do PDF.

### 4. Limpeza Final
* **Script:** `src/scripts/final_cleanup.py`
* **Função:** * Restaura o verso SLK_8.39 (pulado pelo minerador).
    * Preenche o verso SLK_13.47 (vazio).
    * Limpa formatação explodida do SLK_0.1.
    * Remove títulos vazados no SLK_13.87.

---
**Observação:** O banco final foi validado pelo script `audit_slokamrtam.py` e não apresentou erros críticos.