import os
import yaml

def create_structure():
    # Definição da estrutura
    folders = [
        "config",
        "assets/templates",
        "assets/fonts",
        "database/snapshots",
        "downloads",
        "cache",
        "logs/audit_errors",
        "output/01_audio_master",
        "output/02_fasciculos_pdf",
        "output/03_social_media",
        "output/04_legendas_pkg",
        "output/05_source_data",
        "src/harvesters",
        "src/processors",
        "src/intelligence",
        "src/generators",
        "src/utils"
    ]

    print("🚀 Iniciando Setup do Ambiente HariKathaAI...")

    # 1. Criar Pastas
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        # Cria um .gitkeep para o git rastrear pastas vazias
        with open(os.path.join(folder, ".gitkeep"), "w") as f:
            pass
        print(f"✅ Pasta criada: {folder}/")

    # 2. Criar .env de exemplo (se não existir)
    if not os.path.exists(".env"):
        env_content = """# SEGREDOS - NÃO COMPARTILHE
GROQ_API_KEY="gsk_..."
GEMINI_API_KEY="AIza..."
TELEGRAM_BOT_TOKEN="123456:ABC..."
TELEGRAM_CHAT_ID="123456789"
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print("🔑 Arquivo .env criado. Adicione suas chaves lá!")

    # 3. Criar config.yaml (se não existir)
    # (Aqui você pode injetar o conteúdo YAML que mostrei acima)
    if not os.path.exists("config/config.yaml"):
        with open("config/config.yaml", "w") as f:
            f.write("# Cole o conteúdo do YAML aqui")
        print("⚙️ Arquivo config/config.yaml criado.")

    print("\n✨ Ambiente pronto! Estrutura física montada.")

if __name__ == "__main__":
    create_structure()