# 1. Daha kapsamlı bir Python görüntüsü kullan (Hata almamak için)
FROM python:3.9-bookworm

# 2. Uygulama klasörü
WORKDIR /app

# 3. Gerekli sistem araçlarını kur
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Kodları kopyala
COPY . .

# 5. Kütüphaneleri yükle
RUN pip install --no-cache-dir -r requirements.txt

# 6. Port ayarı
EXPOSE 8080

# 7. Çalıştırma komutu
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
