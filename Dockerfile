# Gunakan image Python versi 3.12 yang ringan sebagai dasar (Debian Bullseye)
FROM python:3.12-slim

# Set direktori kerja di dalam kontainer
WORKDIR /app

# --- INSTALASI WKHTMLTOPDF SECARA MANUAL ---
# (Bagian instalasi wkhtmltopdf yang sudah berhasil...)
RUN apt-get update && apt-get install -y \
    wkhtmltopdf xvfb fontconfig \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- LANJUTAN PROSES BUILD ---
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]