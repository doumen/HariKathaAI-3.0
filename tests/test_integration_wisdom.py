import subprocess
import json

def test_node_integration():
    print("🚀 Testando ponte Python -> Node.js...")
    
    # Executa o script JS passando argumentos
    result = subprocess.run(
        ['node', './test_wisdom_fetcher.js', 'Bhakti-rasamrta-sindhu', '1.1.1'],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if result.returncode == 0:
            try:
                # Procura o início do JSON na saída bruta
                raw_output = result.stdout.strip()
                start_index = raw_output.find('{')
                end_index = raw_output.rfind('}') + 1
                
                if start_index != -1 and end_index != 0:
                    json_str = raw_output[start_index:end_index]
                    data = json.loads(json_str)
                    print(f"✅ Sucesso! Referência: {data['referencia']}")
                    print(f"📖 Sânscrito: {data['sânscrito'][:50]}...")
                else:
                    raise ValueError("Nenhum objeto JSON encontrado na saída.")
                    
            except Exception as e:
                print(f"❌ Erro ao processar retorno: {e}")
                print(f"Saída bruta recebida:\n{result.stdout}")    
    else:
        print(f"❌ Erro no Node.js: {result.stderr}")

if __name__ == "__main__":
    test_node_integration()