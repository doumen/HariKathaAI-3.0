import time
import sys
import os

# --- Truque para importar módulos da raiz do projeto ---
# Adiciona a pasta pai da pai (raiz do projeto) ao Python Path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

from integration_main import capture_and_save

# --- Configuração da Mineração ---
LIVRO = "BRS" # Bhakti-rasamrta-sindhu

# Vamos pegar os versos fundamentais do início
versos_alvo = [
    "1.1.2", # Características da Bhakti
    "1.1.3", # Comparação com outros caminhos
    "1.1.4", 
    "1.1.5",
    "1.1.11" # Uttama-bhakti (Definição crucial)
]

print(f"🏭 INICIANDO FÁBRICA DE CONTEÚDO: {LIVRO}")
print(f"🎯 Alvo: {len(versos_alvo)} versos")
print("="*60)

sucessos = 0
erros = 0

for ref in versos_alvo:
    print(f"\n[⏳] Processando {LIVRO} {ref}...")
    try:
        # Chama nosso pipeline validado
        capture_and_save(LIVRO, ref)
        sucessos += 1
        
        # Pausa estratégica para não sermos bloqueados (Seja gentil com o servidor)
        print("   ...Respirando por 5 segundos...")
        time.sleep(5) 
        
    except Exception as e:
        print(f"   [❌] Falha: {e}")
        erros += 1

print("\n" + "="*60)
print(f"🏁 FIM DO TURNO.")
print(f"✅ Sucessos: {sucessos}")
print(f"❌ Erros: {erros}")
print("="*60)