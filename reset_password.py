from app import app, db
from app.models import User
from werkzeug.security import generate_password_hash

# --- Konfigurasi ---
USERNAME_TO_RESET = 'superadmin'
NEW_PASSWORD = 'admin123'

with app.app_context():
    # Cari pengguna berdasarkan username
    user = User.query.filter_by(username=USERNAME_TO_RESET).first()

    if user:
        # Jika pengguna ditemukan, update passwordnya
        user.password = generate_password_hash(NEW_PASSWORD)
        db.session.commit()
        print(f"✅ Password untuk pengguna '{USERNAME_TO_RESET}' telah berhasil direset.")
    else:
        # Jika pengguna tidak ditemukan
        print(f"❌ Pengguna dengan username '{USERNAME_TO_RESET}' tidak ditemukan di database.")