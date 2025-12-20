import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega o .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"🔑 Testando chave: {api_key[:5]}...{api_key[-4:]}") # Mostra só o começo e fim

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    print("📡 Enviando 'Olá' para o Gemini...")
    response = model.generate_content("Diga apenas: 'Conexão Estabelecida'")
    
    print(f"✅ Sucesso! Resposta da IA: {response.text}")

except Exception as e:
    print(f"❌ Erro: {e}")