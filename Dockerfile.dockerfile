# Usa Python como base
FROM python:3.10-slim

# Instala o Node.js e dependências do Chromium para o Puppeteer
RUN apt-get update && apt-get install -y nodejs npm chromium

# Configura o lado Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Configura o lado Node
COPY package.json .
RUN npm install

# Copia o resto do código
COPY . .

CMD ["python", "run_pipeline.py"]