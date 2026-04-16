from app import create_app
from app.commands import setup_database

# Buat instance aplikasi Flask
app = create_app()

# Buat konteks aplikasi secara manual
with app.app_context():
    print("Menjalankan proses setup database...")
    
    # Panggil fungsi setup secara langsung
    setup_database()

print("\nProses setup selesai.")