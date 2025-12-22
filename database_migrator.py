
"""
A partir de agora, seu fluxo de manutenção do banco será:

    database_setup.py: Garante que as tabelas básicas existam (sempre seguro rodar).

    database_migrator.py: Garante que colunas novas de atualizações recentes sejam inseridas em tabelas antigas.

💡 Dica de Ouro: O Campo version

Note que na sua tabela library_content (v6.5) já existe um campo version. Use-o! Se você rodar o scraper novamente e o texto do WisdomLib vier levemente diferente (uma correção gramatical, por exemplo), você pode inserir o novo texto com version = 2 em vez de apagar o anterior.
"""

import sqlite3
import logging

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Migrator")

DB_PATH = "database/harikatha.db"

def add_column_if_not_exists(table_name, column_name, column_type):
    """Adiciona uma coluna a uma tabela se ela ainda não existir."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Verifica as colunas atuais da tabela
        cur.execute(f"PRAGMA table_info({table_name});")
        columns = [column[1] for column in cur.fetchall()]
        
        if column_name not in columns:
            logger.info(f"🆕 Adicionando coluna '{column_name}' na tabela '{table_name}'...")
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
            conn.commit()
            logger.info("✅ Coluna adicionada com sucesso!")
        else:
            # logger.info(f"✔ A coluna '{column_name}' já existe em '{table_name}'.")
            pass
            
    except Exception as e:
        logger.error(f"❌ Erro ao migrar tabela {table_name}: {e}")
    finally:
        conn.close()

def run_migrations():
    logger.info("🚀 Iniciando verificação de integridade do Schema...")
    
    # EXEMPLOS DE MUDANÇAS FUTURAS:
    # Se você decidir que quer guardar o autor do livro:
    add_column_if_not_exists("library_books", "author", "TEXT")
    
    # Se você quiser guardar um resumo da aula gerado por IA:
    add_column_if_not_exists("lectures", "ia_summary", "TEXT")
    
    # Se quiser guardar a versão do modelo usado na transcrição:
    add_column_if_not_exists("pipeline_jobs", "model_version", "TEXT")

    logger.info("🏁 Migrações concluídas.")

if __name__ == "__main__":
    run_migrations()