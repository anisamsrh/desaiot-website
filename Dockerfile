# 1. Gunakan image dasar Python yang ringan (Slim version)

FROM python:3.10-slim



# 2. Set folder kerja di dalam container

WORKDIR /app



# 3. Copy file requirements.txt dulu (biar cache Docker optimal)

COPY requirements.txt .



# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy seluruh sisa kode project kamu ke dalam container
# (Ini termasuk main.py, templates/, dan serviceAccountKey.json)
COPY . .

# 6. Buka port 8000 (Port standar FastAPI)
EXPOSE 8000

# 7. Perintah untuk menjalankan aplikasi saat container start
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

