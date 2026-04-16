# Website Donasi Buku Kabupaten Lumajang

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.3-green)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey)
![License](https://img.shields.io/badge/License-Educational-yellow)

Aplikasi web berbasis Flask yang dirancang untuk memfasilitasi dan mengelola donasi buku dari masyarakat untuk disalurkan ke perpustakaan desa (perpusdes) di seluruh Kabupaten Lumajang.

> **Project Status**: ✅ Active Development | 📚 Educational Project | 🎓 Final Assignment

**Developed by**: Salma Acacia Prasasta  
**Institution**: Universitas Negeri Malang - D4 Perpustakaan Digital  
**For**: Dinas Kearsipan dan Perpustakaan Kabupaten Lumajang

## 🎯 Quick Start

```bash
# Clone repository
git clone https://github.com/your-username/website-donasi.git
cd website-donasi

# Setup virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
# Edit .env dan isi konfigurasi email

# Initialize database
flask db upgrade

# Import initial data
python setup.py

# Run application
python run.py
```

Akses aplikasi di: http://127.0.0.1:5000

**Default Login:**
- Superadmin: `superadmin` / `admin123`
- User Test: `user1` / `user123`

## 📋 Daftar Isi
- [Quick Start](#-quick-start)
- [Fitur Utama](#-fitur-utama)
- [Tumpukan Teknologi](#-tumpukan-teknologi-tech-stack)
- [Prasyarat](#-prasyarat)
- [Instalasi dan Setup](#-instalasi-dan-setup-awal)
- [Menjalankan Aplikasi](#-menjalankan-aplikasi)
- [Struktur Proyek](#-struktur-proyek)
- [Kredensial Awal](#-kredensial-awal)
- [Fitur dan Halaman](#-fitur-dan-halaman)
- [Database](#-database)
- [API Endpoints](#-api-endpoints)
- [Production Deployment](#-production-deployment)
- [Troubleshooting](#-troubleshooting)
- [Support & Contributing](#-support--contributing)

## 🚀 Fitur Utama

### Untuk Donatur (Pengguna Umum)
- **Registrasi & Login**: Sistem autentikasi pengguna dengan enkripsi password (Werkzeug)
- **Formulir Donasi**: Interface yang user-friendly untuk mengisi data donasi buku dengan multiple subjek
- **Bukti Donasi PDF**: Sistem otomatis menghasilkan bukti donasi dalam format PDF (pdfkit)
- **Konfirmasi Donasi**: Upload bukti pengiriman dengan validasi file gambar
- **Transparansi**: Halaman untuk melihat riwayat dan transparansi donasi dengan detail distribusi
- **Portal Berita/Kegiatan**: Sistem berita perpustakaan dengan informasi kegiatan
- **FAQ & Panduan**: Informasi lengkap tentang cara berdonasi dan syarat ketentuan
- **Directory Perpustakaan**: Daftar lengkap perpustakaan desa dengan informasi detail dan lokasi GPS
- **Profil Pengguna**: Manajemen informasi profil donatur

### Untuk Admin Perpustakaan Desa
- **Dashboard Admin**: Panel kontrol dengan statistik kunjungan dan kegiatan perpustakaan
- **Profil Perpustakaan**: Pengelolaan informasi dan profil perpustakaan lengkap dengan foto, deskripsi, dan lokasi GPS
- **Pengajuan Kebutuhan**: Sistem untuk mengajukan kebutuhan koleksi buku dengan multiple subjek dan prioritas
- **Manajemen Kegiatan**: Upload dan kelola berita/kegiatan perpustakaan dengan foto dan deskripsi lengkap
- **Riwayat Distribusi**: Monitoring distribusi buku yang diterima dari donasi
- **Analytics Kunjungan**: Pencatatan dan monitoring kunjungan perpustakaan dengan visualisasi data
- **Upload Bukti**: Upload bukti penerimaan distribusi buku

### Untuk Super Admin (Dinas)
- **Dashboard Komprehensif**: Statistik lengkap donasi, distribusi, dan perpustakaan dengan charts
- **Manajemen Donasi**: Verifikasi, penolakan, dan distribusi donasi dengan detail lengkap per subjek
- **Manajemen Perpustakaan**: CRUD operations dengan import Excel dan bulk operations
- **Verifikasi Admin**: Sistem verifikasi untuk admin perpustakaan baru
- **Riwayat Distribusi**: Monitoring distribusi dengan status tracking (pengiriman/diterima)
- **Pengajuan Kebutuhan**: Review dan approve pengajuan dari perpustakaan dengan prioritas
- **Kelola Subjek Buku**: Manajemen kategori subjek buku (CRUD)
- **Data Donatur**: Melihat dan mengelola data pengguna/donatur
- **Tampilan Depan**: Kelola konten yang ditampilkan di halaman publik
- **Statistik Real-time**: Dashboard dengan data statistik dan visualisasi

## 🛠 Tumpukan Teknologi (Tech Stack)

### Backend
- **Flask 3.0.3**: Web framework utama
- **Flask-SQLAlchemy**: ORM untuk database operations
- **Flask-Migrate**: Database migration management
- **Flask-Login**: User session management
- **SQLite**: Database (production-ready untuk skala menengah)
- **Werkzeug**: Security utilities dan file handling

### Frontend
- **Jinja2**: Template engine dengan macro system untuk reusability
- **TailwindCSS**: Modern utility-first CSS framework (via CDN)
- **Bootstrap** (optional/legacy): Responsive framework
- **Font Awesome**: Icon library untuk UI
- **jQuery**: DOM manipulation dan AJAX requests
- **JavaScript ES6+**: Modern JavaScript untuk interaktivitas
- **Chart.js** (optional): Data visualization untuk dashboard statistik
- **DataTables** (optional): Enhanced table functionality dengan responsive design

### Libraries & Tools
- **Pandas**: Data processing untuk import Excel
- **pdfkit**: PDF generation untuk bukti donasi
- **Pillow (PIL)**: Image processing untuk upload gambar (tidak terinstall, perlu ditambahkan jika digunakan)
- **python-dotenv**: Environment variable management
- **pytz**: Timezone handling untuk WIB
- **OpenPyXL**: Excel file handling
- **Requests**: HTTP library untuk API calls
- **Alembic**: Database migration tool (via Flask-Migrate)
- **Gunicorn**: Production WSGI HTTP Server
- **Flask-CORS**: Cross-Origin Resource Sharing support

## 📋 Prasyarat

Pastikan sistem Anda telah terinstal:

1. **Python 3.8+**: Preferably Python 3.10 atau lebih baru
2. **Git**: Untuk version control dan cloning repository
3. **wkhtmltopdf**: Required untuk PDF generation (opsional jika tidak menggunakan fitur PDF)
   - Download dari [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html)
   - **Windows**: Install di `C:\Program Files\wkhtmltopdf\`
   - **Linux**: `sudo apt-get install wkhtmltopdf` (Ubuntu/Debian)
   - **macOS**: `brew install wkhtmltopdf`

## 🔧 Instalasi dan Setup Awal

### 1. Clone Repository
```bash
git clone https://github.com/your-username/website-donasi.git
cd website-donasi
```

### 2. Buat Virtual Environment
```bash
# Menggunakan venv (built-in Python)
python -m venv venv

# Aktivasi environment
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# ATAU menggunakan conda
conda create --name donasi-env python=3.10
conda activate donasi-env
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment
Copy file `.env.example` menjadi `.env` dan isi dengan nilai yang sesuai:
```bash
# Copy template environment file
# Windows PowerShell
copy .env.example .env
# Linux/macOS
cp .env.example .env

# Edit file .env dengan editor favorit Anda
# Windows
notepad .env
# Linux/macOS
nano .env
# atau gunakan VS Code
code .env
```

File `.env` minimal harus berisi:
```env
# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Flask Configuration (opsional)
FLASK_DEBUG=True
FLASK_PORT=5000
FLASK_HOST=127.0.0.1
SECRET_KEY=dev-secret-key-change-in-production
```

**Catatan penting:**
- Untuk production, ganti `SECRET_KEY` dengan key yang aman
- Gunakan App Password untuk Gmail (bukan password biasa)
- Email configuration diperlukan untuk fitur notifikasi

### 5. Setup Database
```bash
# Initialize migration repository (hanya sekali di awal)
flask db init

# Create initial migration
flask db migrate -m "Initial database migration"

# Apply migration to create tables
flask db upgrade
```

**Catatan:** Jika folder `migrations/` sudah ada, skip langkah `flask db init`.

## 🛠 Utility Scripts

Project ini dilengkapi dengan beberapa utility scripts untuk maintenance:

### setup.py
Setup awal database dengan data default:
```bash
python setup.py
```
Membuat:
- Akun superadmin dan user test
- Import perpustakaan dari Excel
- Generate admin untuk setiap perpustakaan
- Setup subjek buku default
- Create dummy data untuk testing

### reset_password.py
Reset password user tertentu:
```bash
# Edit file reset_password.py terlebih dahulu
# Ubah USERNAME_TO_RESET dan NEW_PASSWORD sesuai kebutuhan
python reset_password.py
```

### Commands Available (Flask CLI)
```bash
# Jika ada custom commands di app/commands.py
flask --help  # Lihat semua commands tersedia
```

### 6. Import Data Awal
Pastikan file `DATA PERPUSDES & TBM.xlsx` ada di root directory, kemudian:
```bash
python setup.py
```

Script ini akan:
- Membuat akun superadmin default (username: `superadmin`, password: `admin123`)
- Membuat 3 akun user dummy untuk testing
- Import data perpustakaan dari Excel
- Setup admin untuk setiap perpustakaan secara otomatis
- Import subjek buku default
- Generate data dummy donasi, kegiatan, dan kebutuhan koleksi

**Format Excel yang dibutuhkan:**
- File: `DATA PERPUSDES & TBM.xlsx`
- Kolom: `NAMA PESPUSTAKAAN`, `DESA/KEL`, `KECAMATAN`

## 🚀 Menjalankan Aplikasi

### Development Mode
```bash
# Cara 1: Menggunakan run.py (Recommended)
python run.py

# Cara 2: Menggunakan Flask CLI
flask run --debug
```

### Production Mode
```bash
# Menggunakan Gunicorn (Linux/macOS)
gunicorn -w 4 -b 0.0.0.0:8000 run:app

# Atau menggunakan run.py dengan konfigurasi production
# Set environment variable terlebih dahulu
# Windows PowerShell
$env:FLASK_DEBUG="False"; python run.py
# Linux/macOS
FLASK_DEBUG=False python run.py
```

Aplikasi akan berjalan di: **http://127.0.0.1:5000** (default)

**Catatan:**
- Port dan host dapat diubah melalui environment variable `FLASK_PORT` dan `FLASK_HOST`
- Debug mode dapat dinonaktifkan dengan set `FLASK_DEBUG=False` di file `.env`

## 📁 Struktur Proyek

```
website-donasi/
├── app/
│   ├── __init__.py          # App factory dan konfigurasi
│   ├── models.py            # Database models (13 models)
│   ├── commands.py          # CLI commands untuk setup dan import data
│   ├── controllers/         # Route handlers (terorganisir per modul)
│   │   ├── __init__.py      # Controller registration
│   │   ├── public_routes.py # Public routes
│   │   ├── admin_routes.py  # Admin perpustakaan routes
│   │   └── superadmin_routes.py # Superadmin routes
│   ├── utils/               # Utility modules
│   │   ├── auth_decorators.py   # Custom decorators untuk auth
│   │   ├── email_utils.py       # Email sending utilities
│   │   └── session_manager.py   # Session management
│   ├── static/              # Asset files
│   │   ├── style.css        # Custom stylesheet
│   │   ├── images/          # Static images
│   │   ├── pdf/             # Generated PDF files
│   │   ├── public/          # Public uploaded files
│   │   │   ├── bukti-distribusi/  # Bukti distribusi
│   │   │   ├── bukti-pengiriman/  # Bukti pengiriman donasi
│   │   │   ├── foto-perpus/       # Foto perpustakaan
│   │   │   ├── kegiatan-perpus/   # Foto kegiatan
│   │   │   ├── sampul-buku/       # Sampul buku
│   │   │   └── sertifikat-donasi/ # Sertifikat donasi
│   │   └── uploads/         # Admin uploaded files
│   │       └── resi/        # Upload resi pengiriman
│   └── templates/           # Jinja2 templates dengan macro system
│       ├── base.html        # Base template utama
│       ├── pengguna/        # User-facing templates (23 files)
│       │   ├── base_public.html
│       │   ├── content_wrapper.html
│       │   ├── navbar.html
│       │   ├── footer.html
│       │   ├── index.html
│       │   ├── form_donasi.html
│       │   ├── konfirmasi_donasi.html
│       │   ├── transparansi_donasi.html
│       │   ├── riwayat_transparansi.html
│       │   ├── perpusdes.html
│       │   ├── detail_perpusdes.html
│       │   ├── semua_berita.html
│       │   ├── detail_berita.html
│       │   └── ...
│       ├── admin/           # Admin perpustakaan templates (12 files)
│       │   ├── base_admin.html
│       │   ├── sidebar.html
│       │   ├── dashboard.html
│       │   ├── profil_perpustakaan.html
│       │   ├── kebutuhan_koleksi.html
│       │   ├── kegiatan_perpus.html
│       │   ├── kunjungan_analytics.html
│       │   └── ...
│       └── superadmin/      # Superadmin templates (15+ files)
│           ├── base_superadmin.html
│           ├── content_wrapper.html
│           ├── statistik.html
│           ├── donasi.html
│           ├── perpusdesa.html
│           ├── riwayat_distribusi.html
│           ├── pengajuan_perpusdes.html
│           ├── kelola_subjek.html
│           └── ...
├── instance/
│   └── users.db             # SQLite database
├── migrations/              # Database migrations (Alembic)
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── backup_volumes/          # Backup directory
├── .env.example             # Environment variables template
├── config.py               # Configuration classes
├── requirements.txt         # Python dependencies
├── run.py                  # Application entry point
├── setup.py                # Initial setup script
├── reset_password.py       # Password reset utility
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── DEPLOY.md               # Deployment documentation
└── README.md               # Project documentation
```

## 🔑 Kredensial Awal

Setelah menjalankan `python setup.py`, berikut adalah kredensial default yang tersedia:

### Super Admin
- **URL**: `/superadmin/login`
- **Username**: `superadmin`
- **Password**: `admin123`
- **Email**: `admin@lumajang.go.id`

### User Test (Donatur)
- **URL**: `/login`
- **User 1**: `user1` / `user123` (Ahmad Donatur)
- **User 2**: `user2` / `user123` (Siti Dermawan)
- **User 3**: `user3` / `user123` (Budi Peduli)

### Admin Perpustakaan (Auto-generated dari Excel)
- **URL**: `/login-admin`
- **Format Username**: `{nama_perpus}_{kecamatan}` (lowercase, spasi jadi underscore)
- **Format Password**: `{nama_desa_tanpa_spasi}123` (lowercase)

Contoh:
- **Perpustakaan**: "Perpustakaan Ceria" di Desa "Kloposawit", Kecamatan "Candipuro"
- **Username**: `perpustakaan_ceria_candipuro`
- **Password**: `kloposawit123`

**⚠️ PENTING:** Segera ubah password default setelah login pertama kali, terutama untuk production!

## 📱 Fitur dan Halaman

### Ringkasan Fitur per Role

| Fitur | Donatur | Admin Perpus | Super Admin |
|-------|---------|--------------|-------------|
| Registrasi & Login | ✅ | ✅ (auto-created) | ✅ |
| Dashboard | ❌ | ✅ | ✅ |
| Form Donasi Buku | ✅ | ❌ | ❌ |
| Upload Bukti Pengiriman | ✅ | ❌ | ❌ |
| Download PDF Bukti Donasi | ✅ | ❌ | ✅ |
| Lihat Transparansi Donasi | ✅ | ✅ | ✅ |
| Kelola Profil Perpustakaan | ❌ | ✅ | ✅ |
| Ajukan Kebutuhan Koleksi | ❌ | ✅ | ❌ |
| Input Kunjungan Perpus | ❌ | ✅ | ❌ |
| Posting Berita/Kegiatan | ❌ | ✅ | ❌ |
| Verifikasi Donasi | ❌ | ❌ | ✅ |
| Distribusi Buku | ❌ | ❌ | ✅ |
| Kelola Perpustakaan (CRUD) | ❌ | ❌ | ✅ |
| Kelola Subjek Buku | ❌ | ❌ | ✅ |
| Lihat Statistik Lengkap | ❌ | ✅ (terbatas) | ✅ |

### Pengguna Umum
| URL | Deskripsi | Status |
|-----|-----------|---------|
| `/` | Halaman utama dengan berita terkini | ✅ |
| `/register` | Registrasi pengguna baru | ✅ |
| `/login` | Login pengguna | ✅ |
| `/formulir-donasi` | Form donasi buku multi-subjek | ✅ |
| `/konfirmasi-donasi/<id>` | Upload bukti pengiriman | ✅ |
| `/unduh-bukti-donasi/<id>` | Download PDF bukti donasi | ✅ |
| `/riwayat-transparansi` | Transparansi donasi dengan detail distribusi | ✅ |
| `/perpusdes` | Directory perpustakaan desa | ✅ |
| `/berita` | Portal berita dengan search & pagination | ✅ |
| `/berita/<perpus_slug>/<slug>` | Detail berita | ✅ |
| `/profil` | Profil pengembang | ✅ |

### Admin Perpustakaan
| URL | Deskripsi | Status |
|-----|-----------|---------|
| `/login-admin` | Login admin | ✅ |
| `/admin/dashboard` | Dashboard dengan statistik | ✅ |
| `/admin/profil-perpustakaan` | Manajemen profil perpustakaan | ✅ |
| `/admin/kebutuhan-koleksi` | Pengajuan kebutuhan koleksi | ✅ |
| `/admin/kunjungan-perpus` | Manajemen data kunjungan | ✅ |
| `/admin/berita-kegiatan` | Manajemen berita/kegiatan | ✅ |
| `/admin/riwayat-distribusi` | Monitoring distribusi | ✅ |

### Super Admin
| URL | Deskripsi | Status |
|-----|-----------|---------|
| `/superadmin/login` | Login superadmin | ✅ |
| `/superadmin/dashboard` | Dashboard komprehensif | ✅ |
| `/superadmin/donasi` | Manajemen donasi lengkap | ✅ |
| `/superadmin/perpusdes` | Manajemen perpustakaan | ✅ |
| `/superadmin/verifikasi-admin` | Verifikasi admin baru | ✅ |
| `/superadmin/riwayat-distribusi` | Manajemen distribusi | ✅ |
| `/superadmin/pengajuan-perpusdes` | Review pengajuan kebutuhan | ✅ |
| `/superadmin/subjek-buku` | Manajemen kategori subjek | ✅ |

## 🗄 Database

### Models Utama (13 Models)
1. **User**: Data pengguna dan kredensial login dengan role-based access
2. **Donasi**: Data donasi utama dengan status tracking (draft, pending, confirmed)
3. **DetailDonasi**: Detail buku per subjek yang didonasikan dengan tracking diterima/ditolak
4. **PerpusDesa**: Data perpustakaan desa lengkap
5. **DetailPerpus**: Detail profil perpustakaan (foto, deskripsi, jam operasional, GPS)
6. **SubjekBuku**: Master data kategori subjek buku
7. **KebutuhanKoleksi**: Pengajuan kebutuhan koleksi dengan status approval
8. **DetailKebutuhanKoleksi**: Detail buku yang dibutuhkan per subjek
9. **RiwayatDistribusi**: Tracking distribusi buku ke perpustakaan
10. **DetailRiwayatDistribusi**: Detail distribusi per subjek dan donasi
11. **Kunjungan**: Data kunjungan harian perpustakaan
12. **KegiatanPerpus**: Berita dan kegiatan perpustakaan dengan foto dan lokasi GPS
13. **AdminPerpus** (deprecated - diganti dengan relasi User.perpus_id)

### Relasi Antar Model
- User → PerpusDesa (one-to-one untuk admin perpus)
- Donasi → User (many-to-one)
- Donasi → DetailDonasi (one-to-many)
- DetailDonasi → SubjekBuku (many-to-one)
- PerpusDesa → DetailPerpus (one-to-one)
- PerpusDesa → KebutuhanKoleksi (one-to-many)
- PerpusDesa → RiwayatDistribusi (one-to-many)
- PerpusDesa → KegiatanPerpus (one-to-many)
- PerpusDesa → Kunjungan (one-to-many)

### Database Migration
```bash
# Membuat migration baru setelah perubahan model
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade

# Check migration status
flask db current
flask db history
```

### Timezone Handling
Semua timestamp menggunakan WIB (Asia/Jakarta) timezone melalui helper function `get_wib_datetime()`.

## 📁 File Upload & Static Files

### Upload Folders
Aplikasi menggunakan berbagai folder untuk menyimpan file upload:

```
app/static/
├── public/                    # Public accessible uploads
│   ├── bukti-distribusi/     # Bukti distribusi dari perpustakaan
│   ├── bukti-pengiriman/     # Bukti pengiriman dari donatur
│   ├── foto-perpus/          # Foto profil perpustakaan
│   ├── kegiatan-perpus/      # Foto kegiatan perpustakaan
│   ├── sampul-buku/          # Sampul buku (jika ada)
│   └── sertifikat-donasi/    # Sertifikat untuk donatur
└── uploads/
    └── resi/                  # Resi pengiriman
```

### File Upload Limits
- **Max File Size**: 2MB (dapat diubah di `config.py`)
- **Allowed Extensions**: JPG, JPEG, PNG, GIF
- **Validation**: Server-side validation untuk file type dan size

### Static Files
- **CSS**: `app/static/style.css`
- **Images**: `app/static/images/`
- **PDF**: `app/static/pdf/` (generated PDFs)

**Catatan**: Pastikan folder-folder ini memiliki permission yang tepat untuk write access.

## 🔌 API Endpoints

### Public API
- `GET /api/perpustakaan` - Daftar perpustakaan dengan pagination (jika diimplementasikan)
- `GET /api/berita` - Daftar berita publik (jika diimplementasikan)

### Admin API
- `GET /admin/api/kunjungan-chart` - Data chart kunjungan (jika diimplementasikan)

### Superadmin API
- `GET /superadmin/api/subjects` - Daftar subjek buku (jika diimplementasikan)
- `GET /superadmin/api/available-donations` - Donasi tersedia untuk distribusi (jika diimplementasikan)
- `POST /superadmin/api/bulk-delete` - Bulk operations (jika diimplementasikan)

**Catatan:** API endpoints di atas mungkin belum sepenuhnya diimplementasikan. Periksa file route untuk detail lengkap.

## ⚙️ Configuration

### Environment Variables

Aplikasi mendukung konfigurasi melalui file `.env`:

```env
# Flask Configuration
FLASK_DEBUG=True                    # Debug mode (False untuk production)
FLASK_PORT=5000                     # Port aplikasi (default: 5000)
FLASK_HOST=127.0.0.1               # Host aplikasi (0.0.0.0 untuk public access)
SECRET_KEY=your-secret-key-here    # Secret key untuk session (wajib diubah di production)

# Database Configuration
DATABASE_URL=sqlite:///users.db    # Database URL (default: SQLite)

# Email Configuration (untuk notifikasi)
MAIL_SERVER=smtp.gmail.com         # SMTP server
MAIL_PORT=587                      # SMTP port
MAIL_USE_TLS=true                  # Use TLS
MAIL_USERNAME=your-email@gmail.com # Email username
MAIL_PASSWORD=your-app-password    # Email password (gunakan App Password untuk Gmail)
MAIL_DEFAULT_SENDER=your-email@gmail.com # Default sender

# File Upload Configuration (optional, default sudah di config.py)
MAX_CONTENT_LENGTH=2097152         # Max file size in bytes (2MB default)
```

### Config Classes
Aplikasi menggunakan config classes di `config.py`:
- **DevelopmentConfig**: Untuk development (DEBUG=True)
- **ProductionConfig**: Untuk production (DEBUG=False)
- **TestingConfig**: Untuk testing

### Important Settings
- **SECRET_KEY**: Sangat penting untuk session security. Gunakan key yang kuat di production
- **SQLALCHEMY_DATABASE_URI**: Default SQLite, bisa diubah ke PostgreSQL/MySQL
- **MAX_CONTENT_LENGTH**: Limit ukuran file upload (default 2MB)
- **UPLOAD_FOLDER**: Lokasi penyimpanan file upload

## 🐛 Troubleshooting

### Error: "wkhtmltopdf not found"
**Solusi**: 
- Pastikan wkhtmltopdf terinstall (jika menggunakan fitur PDF)
- Periksa path di `config.py` atau environment variables
- Windows: Pastikan installed di `C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe`
- Restart aplikasi setelah instalasi
- Jika tidak menggunakan fitur PDF, abaikan error ini

### Error Database Migration
**Solusi**:
```bash
# Backup data jika ada
# Windows PowerShell
copy instance\users.db instance\users_backup.db
# Linux/macOS
cp instance/users.db instance/users_backup.db

# Reset migrations (jika diperlukan)
# Hapus folder migrations dan database
# Windows PowerShell
Remove-Item -Recurse -Force migrations; Remove-Item instance\users.db
# Linux/macOS
rm -rf migrations/ instance/users.db

# Buat ulang migrations
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Re-import data
python setup.py
```

### Error Import Excel
**Solusi**:
- Pastikan file `DATA PERPUSDES & TBM.xlsx` ada di root directory
- Periksa format kolom Excel: `NAMA PESPUSTAKAAN`, `DESA/KEL`, `KECAMATAN`
- Install dependencies: `pip install pandas openpyxl`
- Periksa encoding file Excel (gunakan UTF-8)
- Pastikan tidak ada baris kosong di tengah data

### Upload File Error
**Solusi**:
- Pastikan folder `app/static/uploads/` dan subdirectories exists
- Periksa permissions folder uploads (Linux/macOS: `chmod 755`)
- Validasi file size (max 2MB untuk resi)
- Check disk space tersedia
- Pastikan file type yang di-upload sesuai (image untuk foto)

### Port Already in Use
**Solusi**:
```bash
# Gunakan port lain
# Edit .env file, ubah FLASK_PORT=8000

# Atau kill process yang menggunakan port 5000
# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process -Force

# Linux/macOS
lsof -ti:5000 | xargs kill -9
```

### Error "ModuleNotFoundError"
**Solusi**:
```bash
# Pastikan virtual environment aktif
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Locked Error (SQLite)
**Solusi**:
```bash
# Enable WAL mode untuk better concurrency
sqlite3 instance/users.db "PRAGMA journal_mode=WAL;"

# Atau gunakan PostgreSQL/MySQL untuk production
```

## 🚀 Production Deployment

### Using Docker (Recommended)
Project sudah dilengkapi dengan `Dockerfile` dan `docker-compose.yml`:

```bash
# Build dan jalankan dengan Docker Compose
docker-compose up -d

# Atau build manual
docker build -t website-donasi .
docker run -p 5000:5000 website-donasi
```

### Manual Deployment

#### Environment Setup
```bash
# Set production environment
# Linux/macOS
export FLASK_DEBUG=False
export SECRET_KEY=your-production-secret-key-here

# Windows PowerShell
$env:FLASK_DEBUG="False"
$env:SECRET_KEY="your-production-secret-key-here"
```

#### Using Gunicorn (Linux/macOS)
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn (4 workers)
gunicorn -w 4 -b 0.0.0.0:8000 run:app

# Dengan logging
gunicorn -w 4 -b 0.0.0.0:8000 --access-logfile - --error-logfile - run:app
```

#### Using Waitress (Windows)
```bash
# Install waitress
pip install waitress

# Run with waitress
waitress-serve --port=8000 run:app
```

### Database Optimization
```bash
# Enable SQLite WAL mode for better performance
sqlite3 instance/users.db "PRAGMA journal_mode=WAL;"

# Analyze database
sqlite3 instance/users.db "ANALYZE;"

# Untuk production scale, pertimbangkan migrasi ke PostgreSQL/MySQL
```

### Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/website-donasi/app/static;
        expires 30d;
    }
}
```

### Security Checklist
- [x] Change default admin passwords (`superadmin:admin123`)
- [x] Set strong SECRET_KEY di environment variables
- [ ] Enable HTTPS in production (gunakan Let's Encrypt)
- [x] Configure proper file upload limits (sudah di config.py)
- [ ] Set up regular database backups (gunakan cron job)
- [ ] Monitor application logs
- [ ] Set proper file permissions (755 untuk folders, 644 untuk files)
- [ ] Disable debug mode (`FLASK_DEBUG=False`)
- [ ] Use environment variables untuk sensitive data

## 📊 Monitoring & Analytics

### Key Metrics
- Total donasi received & distributed
- Active perpustakaan count  
- User engagement metrics
- Distribution efficiency
- Popular subjek categories
- Kunjungan perpustakaan statistics

### Log Files
Untuk implementasi logging yang lebih baik, tambahkan konfigurasi logging di `app/__init__.py`:

```python
import logging
from logging.handlers import RotatingFileHandler

# Setup logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Website Donasi startup')
```

## 📞 Support & Contributing

### Common Issues & Best Practices

#### Before Starting Development
1. ✅ Pastikan Python 3.8+ terinstall
2. ✅ Gunakan virtual environment
3. ✅ Setup file `.env` dengan benar
4. ✅ Install semua dependencies dari `requirements.txt`
5. ✅ Jalankan migration database
6. ✅ Import data awal dengan `setup.py`

#### Development Workflow
1. Buat branch baru untuk setiap feature: `git checkout -b feature/nama-feature`
2. Test perubahan di local environment
3. Commit dengan message yang jelas
4. Push dan buat Pull Request
5. Request review dari team member

#### Code Quality
- Use consistent indentation (4 spaces)
- Add comments untuk logic yang kompleks
- Follow Flask best practices
- Validate input dari user
- Handle errors dengan graceful degradation

### Getting Help
1. Periksa bagian [Troubleshooting](#-troubleshooting)
2. Review existing GitHub issues di [repository](https://github.com/your-username/website-donasi)
3. Create detailed bug report dengan steps to reproduce
4. Hubungi developer melalui GitHub

### Contributing
Contributions are welcome! Untuk berkontribusi:

1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Development Guidelines
- Follow PEP 8 Python style guide
- Use meaningful commit messages (Conventional Commits)
- Write docstrings untuk functions dan classes
- Test changes sebelum commit
- Update documentation untuk perubahan API/features
- Use virtual environment untuk development
- Jangan commit sensitive data (.env, database files)

### Code Review Process
- Minimal 1 reviewer approval
- Pastikan tidak ada breaking changes
- Update README jika ada perubahan struktur/fitur
- Test di local environment terlebih dahulu

### Technology Decisions
- **Flask**: Lightweight, flexible, mature ecosystem, cocok untuk project skala menengah
- **SQLite**: Zero-configuration, reliable, sufficient untuk project scale (bisa upgrade ke PostgreSQL)
- **TailwindCSS**: Utility-first, responsive, maintainable, rapid development
- **Jinja2**: Powerful templating dengan macro system untuk reusability
- **No JavaScript Framework**: Vanilla JS + jQuery untuk simplicity dan performance

## ❓ FAQ (Frequently Asked Questions)

### Pertanyaan Umum

**Q: Apakah wkhtmltopdf wajib diinstall?**  
A: Hanya jika Anda menggunakan fitur generate PDF bukti donasi. Jika tidak, aplikasi tetap bisa berjalan tanpa wkhtmltopdf.

**Q: Bagaimana cara mengganti port aplikasi?**  
A: Edit file `.env` dan ubah nilai `FLASK_PORT=5000` ke port yang diinginkan, atau jalankan dengan `flask run --port=8000`

**Q: Apakah bisa menggunakan database selain SQLite?**  
A: Ya, bisa. Ubah `DATABASE_URL` di `.env` ke PostgreSQL atau MySQL. Contoh: `postgresql://user:password@localhost/dbname`

**Q: Bagaimana cara menambah subjek buku baru?**  
A: Login sebagai superadmin, masuk ke menu "Kelola Subjek Buku", kemudian tambah subjek baru.

**Q: File Excel untuk import perpustakaan tidak ditemukan?**  
A: Pastikan file `DATA PERPUSDES & TBM.xlsx` ada di root directory project, sejajar dengan `run.py`

**Q: Error "No module named 'app'"?**  
A: Pastikan Anda menjalankan command dari root directory project, dan virtual environment sudah aktif.

**Q: Bagaimana cara backup database?**  
A: Copy file `instance/users.db` ke lokasi backup. Untuk production, setup automated backup dengan cron job.

**Q: Apakah support multiple language?**  
A: Saat ini hanya support Bahasa Indonesia. Multi-language bisa ditambahkan dengan Flask-Babel.

### Pertanyaan Teknis

**Q: Kenapa migration error "table already exists"?**  
A: Hapus folder `migrations/` dan file database, kemudian buat migration baru dari awal.

**Q: Bagaimana cara deploy ke production server?**  
A: Lihat dokumentasi lengkap di [DEPLOY.md](DEPLOY.md) atau section [Production Deployment](#-production-deployment)

**Q: Apakah perlu setup HTTPS?**  
A: Untuk production, sangat disarankan menggunakan HTTPS. Gunakan Let's Encrypt untuk SSL certificate gratis.

**Q: Bagaimana cara mengubah SECRET_KEY?**  
A: Edit file `.env` dan ubah nilai `SECRET_KEY` dengan string random yang aman. Jangan commit ke Git!

**Q: File upload tidak berfungsi?**  
A: Periksa permission folder `app/static/uploads/` dan pastikan max file size tidak terlampaui (default 2MB).

## 📚 Additional Documentation

- **[DEPLOY.md](DEPLOY.md)** - Panduan deployment lengkap
- **[Flask Documentation](https://flask.palletsprojects.com/)** - Framework documentation
- **[SQLAlchemy Docs](https://docs.sqlalchemy.org/)** - ORM documentation  
- **[Jinja2 Template](https://jinja.palletsprojects.com/)** - Template engine guide

## 📄 License & Credits

### Developer Information
- **Developer**: Salma Acacia Prasasta
- **Institution**: Universitas Negeri Malang
- **Program**: D4 Perpustakaan Digital
- **Supervisor**: Lidya Amalia Rahmania, S.Kom, M.Kom.
- **Repository**: [github.com/your-username/website-donasi](https://github.com/your-username/website-donasi)

### Acknowledgments
- Dinas Kearsipan dan Perpustakaan Kabupaten Lumajang
- Tim perpustakaan desa se-Kabupaten Lumajang
- Masyarakat donatur yang telah berkontribusi
- Universitas Negeri Malang

### Technology Stack Credits
- **Flask** - Web framework by Pallets
- **TailwindCSS** - CSS framework by Tailwind Labs
- **SQLAlchemy** - Python SQL toolkit
- **DataTables** - jQuery plugin for enhanced tables (jika digunakan)
- Dan semua open source libraries yang digunakan

Project ini dikembangkan sebagai Tugas Akhir untuk memajukan literasi masyarakat melalui optimalisasi perpustakaan desa di Kabupaten Lumajang.

---

**Developed with ❤️ for Kabupaten Lumajang**

*"Donasikan buku Anda, hidupkan literasi di perpustakaan desa. Bersama kita maju bersama."*
