# 1. Python'ın hafif bir sürümünü temel al
FROM python:3.9-slim

# 2. Uygulama klasörünü oluştur
WORKDIR /app

# 3. Sistem bağımlılıklarını güncelle (Gerekli araçlar için)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# 4. Kodlarımızı ve kütüphane listesini içeri kopyala
COPY . .

# 5. Kütüphaneleri yükle
RUN pip install --no-cache-dir -r requirements.txt

# 6. Google Cloud Run genelde 8080 portunu kullanır
EXPOSE 8080

# 7. Uygulamayı uçuşa geçiren komut (Antigravity modu!)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
