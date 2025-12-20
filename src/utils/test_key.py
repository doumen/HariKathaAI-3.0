import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# Apenas conta os tokens, não gera conteúdo (é mais leve para a cota)
print(model.count_tokens("Teste"))