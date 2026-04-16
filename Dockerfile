# Gunakan image Python yang menggunakan Debian Bullseye secara spesifik
FROM python:3.10-slim-bullseye

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
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:create_app()"]