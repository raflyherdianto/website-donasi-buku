from .models import db, User, PerpusDesa, KegiatanPerpus, KebutuhanKoleksi, DetailKebutuhanKoleksi, SubjekBuku, \
                    DetailPerpus, get_wib_datetime, Donasi, DetailDonasi
from werkzeug.security import generate_password_hash
import pandas as pd
import random
from datetime import datetime, timedelta
import requests
import os

def setup_database():
    """Membuat superadmin dan mengimpor data perpustakaan dengan penanganan error yang lebih baik."""
    
    # --- Setup user awal ---
    try:
        # User yang akan dibuat (Superadmin & Dummy)
        initial_users = [
            {'username': 'superadmin', 'full_name': 'Super Admin', 'email': 'admin@lumajang.go.id', 'password': 'admin123', 'role': 'superadmin'},
            {'username': 'user1', 'full_name': 'Ahmad Donatur', 'email': 'user1@gmail.com', 'password': 'user123', 'role': 'user'},
            {'username': 'user2', 'full_name': 'Siti Dermawan', 'email': 'user2@gmail.com', 'password': 'user123', 'role': 'user'},
            {'username': 'user3', 'full_name': 'Budi Peduli', 'email': 'user3@gmail.com', 'password': 'user123', 'role': 'user'}
        ]
        
        for user_data in initial_users:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'], 
                    full_name=user_data['full_name'], 
                    email=user_data['email'],
                    password=generate_password_hash(user_data['password']), 
                    role=user_data['role'], 
                    is_verified=True,
                    created_at=get_wib_datetime(),
                    updated_at=get_wib_datetime()
                )
                db.session.add(user)
                print(f"✅ User '{user_data['username']}' berhasil dibuat.")
        
        db.session.commit()
    except Exception as e:
        print(f"❌ Error saat membuat user awal: {e}")
        db.session.rollback()

    # --- Impor Data Perpustakaan ---
    print("\n--- Memulai Proses Impor Data Perpustakaan ---")
    try:
        df = pd.read_excel("DATA PERPUSDES & TBM.xlsx")
        df.columns = df.columns.str.strip()
        print(f"INFO: Kolom yang terdeteksi di Excel: {list(df.columns)}")

        COL_NAMA = 'NAMA PESPUSTAKAAN'
        COL_DESA = 'DESA/KEL'
        COL_KEC = 'KECAMATAN'

        impor_berhasil = 0
        for index, row in df.iterrows():
            try:
                nama_perpus_raw = row.get(COL_NAMA)
                desa_raw = row.get(COL_DESA)
                kecamatan_raw = row.get(COL_KEC)

                if pd.isna(nama_perpus_raw) or pd.isna(desa_raw) or pd.isna(kecamatan_raw):
                    continue

                nama_perpus = str(nama_perpus_raw).strip()
                desa = str(desa_raw).replace("Desa ", "").replace("Kelurahan ", "").strip()
                kecamatan = str(kecamatan_raw).strip()
                
                if PerpusDesa.query.filter_by(nama=nama_perpus, desa=desa).first():
                    continue 

                current_time = get_wib_datetime()
                perpus = PerpusDesa(
                    nama=nama_perpus, 
                    desa=desa, 
                    kecamatan=kecamatan,
                    created_at=current_time,
                    updated_at=current_time
                )
                db.session.add(perpus)
                
                username = nama_perpus.lower().replace(" ", "_") + "_" + kecamatan.lower()
                
                if User.query.filter_by(username=username).first():
                    continue

                password_plain = desa.lower().replace(" ", "") + "123"
                admin_user = User(
                    username=username, 
                    full_name=f"Admin {nama_perpus}", 
                    email=f"{username}@perpusdes.id",
                    password=generate_password_hash(password_plain), 
                    role='admin', 
                    is_verified=True, 
                    perpus=perpus,
                    created_at=current_time,
                    updated_at=current_time
                )
                db.session.add(admin_user)

                db.session.commit()
                impor_berhasil += 1

            except Exception as row_error:
                db.session.rollback()
                print(f"  -> ❌ Gagal impor baris {index + 2}: {row_error}")
                continue
        
        print(f"\n✅ Proses impor selesai. Berhasil mengimpor {impor_berhasil} data perpustakaan baru.")

    except FileNotFoundError:
        print("❌ ERROR: File 'DATA PERPUSDES & TBM.xlsx' tidak ditemukan.")
    except Exception as e:
        print(f"❌ Terjadi error besar saat memproses file Excel: {e}")
    
    # --- Setup Subjek Buku ---
    print("\n--- Memulai Setup Subjek Buku ---")
    setup_subjek_buku()
    
    # --- Setup Profil Perpustakaan ---
    print("\n--- Memulai Setup Profil Perpustakaan ---")
    setup_profil_perpustakaan()
    
    # --- Generate Data Dummy ---
    print("\n--- Memulai Proses Generate Data Dummy ---")
    generate_dummy_data()

def setup_subjek_buku():
    """Setup data subjek buku"""
    try:
        subjek_list = [
            'Novel', 'Matematika', 'Sains', 'Agama', 'Bahasa', 'Teknologi',
            'Dongeng', 'Resep Masakan', 'Prakarya', 'Sejarah', 'Majalah',
            'Kamus', 'Peta', 'Alam Semesta', 'Luar Angkasa', 'Planet',
            'Psikologi', 'Filsafat', 'Ilmu Sosial', 'Ilmu Pengetahuan',
            'Seni', 'Olahraga', 'Sastra', 'Geografi', 'Biografi'
        ]
        
        for nama_subjek in subjek_list:
            if not SubjekBuku.query.filter_by(nama=nama_subjek).first():
                subjek = SubjekBuku(
                    nama=nama_subjek,
                    created_at=get_wib_datetime(),
                    updated_at=get_wib_datetime()
                )
                db.session.add(subjek)
                print(f"✅ Subjek '{nama_subjek}' berhasil dibuat.")
        
        db.session.commit()
        print("✅ Setup subjek buku selesai.")
        
    except Exception as e:
        print(f"❌ Error saat setup subjek buku: {e}")
        db.session.rollback()

def setup_profil_perpustakaan():
    """Setup profil perpustakaan untuk perpus_id = 1"""
    try:
        # Check if DetailPerpus for perpus_id = 1 already exists
        existing_detail = DetailPerpus.query.filter_by(perpus_id=1).first()
        
        if existing_detail:
            print("✅ Profil perpustakaan untuk perpus_id = 1 sudah ada.")
            return
        
        # Get perpus with id = 1
        perpus = PerpusDesa.query.get(1)
        if not perpus:
            print("❌ Perpustakaan dengan ID 1 tidak ditemukan.")
            return
        
        # Create DetailPerpus record
        detail_perpus = DetailPerpus(
            perpus_id=1,
            penanggung_jawab="Siti Aminah, S.Pd",
            foto_perpus="logo2.png",  # Using existing logo2.png
            deskripsi="Perpustakaan Desa yang melayani masyarakat dengan koleksi buku yang beragam dan fasilitas yang nyaman untuk belajar dan membaca.",
            latar_belakang="Didirikan untuk meningkatkan literasi masyarakat desa dan mendukung program pendidikan berkelanjutan di wilayah ini.",
            jumlah_koleksi=450,
            jumlah_eksemplar=850,
            jam_operasional_mulai=datetime.strptime("08:00", "%H:%M").time(),
            jam_operasional_selesai=datetime.strptime("16:00", "%H:%M").time(),
            koleksi_buku="Novel, Buku Pelajaran, Dongeng Anak, Buku Agama, Majalah, Kamus, Buku Pertanian",
            lokasi="https://www.google.com/maps?q=-8.1335,113.2252",
            latitude=-8.1335,
            longitude=113.2252,
            created_at=get_wib_datetime(),
            updated_at=get_wib_datetime()
        )
        
        db.session.add(detail_perpus)
        db.session.commit()
        
        print(f"✅ Profil perpustakaan berhasil dibuat untuk: {perpus.nama}")
        print(f"   - Penanggung jawab: {detail_perpus.penanggung_jawab}")
        print(f"   - Koleksi: {detail_perpus.jumlah_koleksi} judul, {detail_perpus.jumlah_eksemplar} eksemplar")
        print(f"   - Jam operasional: {detail_perpus.jam_operasional_mulai} - {detail_perpus.jam_operasional_selesai}")
        
    except Exception as e:
        print(f"❌ Error saat setup profil perpustakaan: {e}")
        db.session.rollback()

def create_dummy_kegiatan_perpus():
    """Create 10 dummy kegiatan perpus data"""
    kegiatan_list = [
        {
            'nama_kegiatan': 'Workshop Literasi Digital untuk Anak',
            'deskripsi_kegiatan': '''<h1>Dalam era digital saat ini, penting bagi anak-anak untuk memahami cara menggunakan teknologi dengan bijak dan aman.</h1><br>
            <h2>Materi Workshop.</h2>
<p>Workshop ini mencakup berbagai materi seperti:</p>
<ul>
<li>Pengenalan internet dan media sosial yang aman</li>
<li>Cara mencari informasi yang kredibel</li>
<li>Etika berkomunikasi di dunia maya</li>
</ul><br>
<h3>Manfaat Workshop</h3>
<p>Peserta diharapkan dapat meningkatkan kemampuan literasi digital mereka dan menjadi pengguna internet yang bertanggung jawab.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1335,113.2252'
        },
        {
            'nama_kegiatan': 'Bimbingan Belajar Gratis untuk Siswa SD',
            'deskripsi_kegiatan': '''<h1>Perpustakaan desa mengadakan program bimbingan belajar gratis untuk siswa sekolah dasar.</h1><br>
<h2>Jadwal dan Mata Pelajaran.</h2>
<p>Program ini dilaksanakan setiap hari Senin hingga Jumat dengan mata pelajaran:</p>
<ul>
<li>Matematika</li>
<li>Bahasa Indonesia</li>
<li>IPA</li>
<li>IPS</li>
</ul><br>
<p>Para tutor adalah mahasiswa dan guru volunteer yang berpengalaman dalam mengajar anak-anak.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1298,113.2189'
        },
        {
            'nama_kegiatan': 'Pameran Buku dan Dongeng Bergilir',
            'deskripsi_kegiatan': '''<h1>Acara bulanan yang menampilkan koleksi buku terbaru dan sesi dongeng untuk anak-anak.</h1><br>
<h2>Kegiatan yang Tersedia.</h2>
<ul>
<li>Pameran buku-buku terbaru</li>
<li>Sesi dongeng interaktif</li>
<li>Workshop membuat cerita</li>
<li>Lomba mewarnai untuk anak</li>
</ul><br>
<h3>Tujuan Kegiatan</h3>
<p>Menumbuhkan minat baca sejak dini dan memperkenalkan dunia literasi kepada masyarakat desa.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1401,113.2334'
        },
        {
            'nama_kegiatan': 'Pelatihan Komputer Dasar untuk Ibu-Ibu PKK',
            'deskripsi_kegiatan': '''<h1>Program pemberdayaan perempuan melalui pelatihan teknologi informasi dasar.</h1><br>
<h2>Materi Pelatihan.</h2>
<p>Pelatihan mencakup pembelajaran tentang:</p>
<ul>
<li>Pengenalan komputer dan sistem operasi</li>
<li>Microsoft Word untuk administrasi</li>
<li>Microsoft Excel untuk pembukuan sederhana</li>
<li>Internet dan email</li>
</ul><br>
<h3>Manfaat</h3>
<p>Peserta dapat menggunakan komputer untuk mendukung kegiatan organisasi dan usaha kecil mereka.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1567,113.2445'
        },
        {
            'nama_kegiatan': 'Festival Puisi dan Sastra Daerah',
            'deskripsi_kegiatan': '''<h1>Perayaan kekayaan sastra dan budaya lokal melalui festival puisi dan sastra daerah</h1><br>
<h2>Rangkaian Acara</h2>
<ul>
<li>Kompetisi baca puisi</li>
<li>Pameran karya sastra lokal</li>
<li>Diskusi dengan penulis daerah</li>
<li>Workshop penulisan kreatif</li>
</ul><br>
<h3>Partisipasi Masyarakat</h3>
<p>Festival ini terbuka untuk semua kalangan, dari anak-anak hingga dewasa, untuk mengapresiasi dan melestarikan budaya sastra daerah.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1432,113.2178'
        },
        {
            'nama_kegiatan': 'Kelas Membaca Al-Quran untuk Dewasa',
            'deskripsi_kegiatan': '''<h1>Program pembelajaran membaca Al-Quran khusus untuk orang dewasa yang ingin memperbaiki bacaan mereka</h1><br>
<h2>Program Pembelajaran</h2>
<p>Kelas ini menyediakan:</p>
<ul>
<li>Pembelajaran huruf hijaiyah</li>
<li>Tajwid dasar</li>
<li>Praktek membaca surat-surat pendek</li>
<li>Bimbingan individual</li>
</ul><br>
<h3>Jadwal dan Pengajar</h3>
<p>Kelas diadakan setiap Selasa dan Kamis malam, dibimbing oleh ustadz yang berpengalaman.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1289,113.2367'
        },
        {
            'nama_kegiatan': 'Perpustakaan Keliling ke Dusun Terpencil',
            'deskripsi_kegiatan': '''<h1>Layanan perpustakaan yang datang langsung ke dusun-dusun terpencil untuk memperluas akses literasi</h1><br>
<h2>Layanan yang Disediakan</h2>
<ul>
<li>Peminjaman buku gratis</li>
<li>Sesi membaca bersama</li>
<li>Permainan edukatif</li>
<li>Konsultasi pendidikan</li>
</ul><br>
<h3>Jadwal Kunjungan</h3>
<p>Perpustakaan keliling mengunjungi setiap dusun secara bergilir setiap dua minggu sekali.</p><br>
<p>Program ini bertujuan memastikan semua warga desa dapat mengakses bahan bacaan berkualitas.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1623,113.2289'
        },
        {
            'nama_kegiatan': 'Seminar Parenting dan Pendidikan Anak',
            'deskripsi_kegiatan': '''<h1>Acara edukasi untuk orang tua tentang pola asuh dan pendidikan anak yang efektif</h1><br>
<h2>Topik Pembahasan</h2>
<p>Seminar ini membahas:</p>
<ul>
<li>Komunikasi efektif dengan anak</li>
<li>Mendidik anak di era digital</li>
<li>Menumbuhkan minat baca anak</li>
<li>Mengatasi masalah perilaku anak</li>
</ul><br>
<h3>Narasumber</h3>
<p>Menghadirkan psikolog anak dan praktisi pendidikan berpengalaman.</p><br>
<p>Acara dilengkapi dengan sesi tanya jawab dan konsultasi gratis.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1445,113.2423'
        },
        {
            'nama_kegiatan': 'Klub Diskusi Buku Bulanan',
            'deskripsi_kegiatan': '''<h1>Pertemuan rutin bulanan untuk membahas buku-buku pilihan bersama para pecinta literasi.</h1><br>
<h2>Format Kegiatan.</h2>
<ul>
<li>Pemilihan buku tema bulan ini</li>
<li>Diskusi mendalam tentang isi buku</li>
<li>Sharing pengalaman dan insight</li>
<li>Rekomendasi buku untuk bulan berikutnya</li>
</ul><br>
<h3>Manfaat Bergabung</h3>
<p>Peserta dapat memperluas wawasan, meningkatkan kemampuan berpikir kritis, dan membangun jaringan dengan sesama pecinta buku</p><br>
<p>Klub ini terbuka untuk semua kalangan yang memiliki minat tinggi terhadap literasi.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1356,113.2134'
        },
        {
            'nama_kegiatan': 'Lomba Karya Tulis Ilmiah Remaja',
            'deskripsi_kegiatan': '''<h1>Kompetisi tahunan untuk mendorong minat remaja dalam penelitian dan penulisan ilmiah.</h1><br>
<h2>Kategori Lomba.</h2>
<p>Lomba dibagi dalam beberapa kategori:</p>
<ul>
<li>Ilmu Pengetahuan Alam</li>
<li>Ilmu Pengetahuan Sosial</li>
<li>Teknologi dan Inovasi</li>
<li>Lingkungan dan Keberlanjutan</li>
</ul><br>
<h3>Hadiah dan Apresiasi</h3>
<p>Pemenang akan mendapatkan hadiah menarik, sertifikat, dan kesempatan untuk mempresentasikan karya mereka.</p><br>
<p>Kegiatan ini bertujuan mengembangkan kemampuan riset dan menulis ilmiah sejak dini.</p>''',
            'lokasi': 'https://www.google.com/maps?q=-8.1278,113.2456'
        }
    ]
    
    # Random coordinates for Lumajang area
    locations = [
        (-8.1335, 113.2252), (-8.1298, 113.2189), (-8.1401, 113.2334),
        (-8.1567, 113.2445), (-8.1432, 113.2178), (-8.1289, 113.2367),
        (-8.1623, 113.2289), (-8.1445, 113.2423), (-8.1356, 113.2134),
        (-8.1278, 113.2456)
    ]
    
    for i, kegiatan_data in enumerate(kegiatan_list):
        try:
            # Random date within last 3 months
            base_date = datetime.now() - timedelta(days=random.randint(1, 90))
            lat, lng = locations[i]
            
            # Download and save image
            foto_filename = download_sample_image(f"kegiatan_{i+1}")
            
            kegiatan = KegiatanPerpus(
                user_id=5,  # As requested
                perpus_id=1,  # As requested
                nama_kegiatan=kegiatan_data['nama_kegiatan'],
                tanggal_kegiatan=base_date.date(),
                deskripsi_kegiatan=kegiatan_data['deskripsi_kegiatan'],
                lokasi_kegiatan=f"https://www.google.com/maps?q={lat},{lng}",
                latitude=lat,
                longitude=lng,
                foto_kegiatan=foto_filename,
                status='active',
                created_at=get_wib_datetime(),
                updated_at=get_wib_datetime()
            )
            db.session.add(kegiatan)
            print(f"  ✅ Kegiatan: {kegiatan_data['nama_kegiatan']}")
            
        except Exception as e:
            print(f"  ❌ Error membuat kegiatan {i+1}: {e}")
    
    db.session.commit()

def create_dummy_kebutuhan_koleksi():
    """Create 10 dummy kebutuhan koleksi data with details"""
    kebutuhan_list = [
        {
            'prioritas': 'tinggi',
            'alasan': 'Untuk mendukung program bimbingan belajar dan sesi dongeng yang rutin diadakan setiap minggu',
            'details': [
                {'subjek_id': 7, 'jumlah_buku': 25},  # Dongeng
                {'subjek_id': 2, 'jumlah_buku': 15}   # Matematika
            ]
        },
        {
            'prioritas': 'sedang',
            'alasan': 'Menunjang pelatihan komputer untuk ibu-ibu PKK dan program literasi digital',
            'details': [
                {'subjek_id': 6, 'jumlah_buku': 15},  # Teknologi
                {'subjek_id': 20, 'jumlah_buku': 10}  # Ilmu Pengetahuan
            ]
        },
        {
            'prioritas': 'tinggi',
            'alasan': 'Dibutuhkan untuk mendukung lomba karya tulis ilmiah remaja dan kegiatan penelitian siswa',
            'details': [
                {'subjek_id': 3, 'jumlah_buku': 12}   # Sains
            ]
        },
        {
            'prioritas': 'sedang',
            'alasan': 'Untuk melengkapi koleksi kelas membaca Al-Quran dan kajian keagamaan',
            'details': [
                {'subjek_id': 4, 'jumlah_buku': 20},  # Agama
                {'subjek_id': 23, 'jumlah_buku': 8}   # Sastra
            ]
        },
        {
            'prioritas': 'rendah',
            'alasan': 'Menunjang festival puisi dan sastra daerah serta klub diskusi buku bulanan',
            'details': [
                {'subjek_id': 23, 'jumlah_buku': 18}, # Sastra
                {'subjek_id': 10, 'jumlah_buku': 14}  # Sejarah
            ]
        },
        {
            'prioritas': 'tinggi',
            'alasan': 'Sangat dibutuhkan masyarakat desa yang mayoritas bekerja sebagai petani dan pekebun',
            'details': [
                {'subjek_id': 3, 'jumlah_buku': 12},  # Sains
                {'subjek_id': 9, 'jumlah_buku': 8}    # Prakarya
            ]
        },
        {
            'prioritas': 'sedang',
            'alasan': 'Untuk mendukung seminar parenting dan edukasi kesehatan masyarakat',
            'details': [
                {'subjek_id': 17, 'jumlah_buku': 22}  # Psikologi
            ]
        },
        {
            'prioritas': 'rendah',
            'alasan': 'Mengembangkan potensi ekonomi kreatif dan keterampilan masyarakat desa',
            'details': [
                {'subjek_id': 9, 'jumlah_buku': 16},  # Prakarya
                {'subjek_id': 8, 'jumlah_buku': 10}   # Resep Masakan
            ]
        },
        {
            'prioritas': 'tinggi',
            'alasan': 'Sangat dibutuhkan untuk mendukung program bimbingan belajar gratis siswa SD dan SMP',
            'details': [
                {'subjek_id': 2, 'jumlah_buku': 30},  # Matematika
                {'subjek_id': 5, 'jumlah_buku': 15}   # Bahasa
            ]
        },
        {
            'prioritas': 'sedang',
            'alasan': 'Untuk melestarikan sejarah dan budaya lokal serta mendukung penelitian komunitas',
            'details': [
                {'subjek_id': 10, 'jumlah_buku': 14}, # Sejarah
                {'subjek_id': 24, 'jumlah_buku': 8}   # Geografi
            ]
        }
    ]
    
    # Random locations in Lumajang area
    locations = [
        'https://www.google.com/maps?q=-8.1335,113.2252',
        'https://www.google.com/maps?q=-8.1298,113.2189',
        'https://www.google.com/maps?q=-8.1401,113.2334',
        'https://www.google.com/maps?q=-8.1567,113.2445',
        'https://www.google.com/maps?q=-8.1432,113.2178',
        'https://www.google.com/maps?q=-8.1289,113.2367',
        'https://www.google.com/maps?q=-8.1623,113.2289',
        'https://www.google.com/maps?q=-8.1445,113.2423',
        'https://www.google.com/maps?q=-8.1356,113.2134',
        'https://www.google.com/maps?q=-8.1278,113.2456'
    ]
    
    for i, kebutuhan_data in enumerate(kebutuhan_list):
        try:
            # Random date within last 2 months
            base_date = datetime.now() - timedelta(days=random.randint(1, 60))
            
            # Create main kebutuhan record
            kebutuhan = KebutuhanKoleksi(
                perpus_id=1,  # As requested
                prioritas=kebutuhan_data['prioritas'],
                lokasi=locations[i],
                alasan=kebutuhan_data['alasan'],
                tanggal_pengajuan=base_date,
                status=random.choice(['pending', 'approved', 'rejected']),
                created_at=get_wib_datetime(),
                updated_at=get_wib_datetime()
            )
            db.session.add(kebutuhan)
            db.session.flush()  # Get the kebutuhan.id
            
            # Create detail records
            for detail_data in kebutuhan_data['details']:
                detail = DetailKebutuhanKoleksi(
                    kebutuhan_id=kebutuhan.id,
                    subjek_id=detail_data['subjek_id'],
                    jumlah_buku=detail_data['jumlah_buku'],
                    created_at=get_wib_datetime(),
                    updated_at=get_wib_datetime()
                )
                db.session.add(detail)
            
            print(f"  ✅ Kebutuhan {i+1}: {kebutuhan_data['prioritas']} - {len(kebutuhan_data['details'])} detail")
            
        except Exception as e:
            print(f"  ❌ Error membuat kebutuhan {i+1}: {e}")
    
    db.session.commit()

def create_dummy_donasi():
    """Create dummy Donasi and DetailDonasi entries."""
    try:
        # Ambil user dengan id 2, 3, dan 4
        user_ids = [2, 3, 4]
        subjek_list = SubjekBuku.query.all()
        
        for user_id in user_ids:
            user = User.query.get(user_id)
            if not user:
                print(f"⚠️ User dengan id={user_id} tidak ditemukan, skip.")
                continue

            # Buat 1-2 donasi per user untuk variasi data
            for _ in range(random.randint(1, 2)):
                # Buat invoice unik sesuai format DNSI<NAMA_DEPAN><6 digit angka>
                nama_depan = user.full_name.split()[0].upper()
                while True:
                    rand6 = ''.join(random.choices('0123456789', k=6))
                    invoice = f"DNSI{nama_depan}{rand6}"
                    if not Donasi.query.filter_by(invoice=invoice).first():
                        break

                donasi = Donasi(
                    user_id=user.id,
                    invoice=invoice,
                    whatsapp="08123456789",
                    metode=random.choice(['mandiri']),
                    status=random.choice(['draft','pending','confirmed']),
                    created_at=get_wib_datetime(),
                    updated_at=get_wib_datetime()
                )
                db.session.add(donasi)
                db.session.flush()

                # buat 2-4 detail donasi per invoice
                for _ in range(random.randint(2,4)):
                    sub = random.choice(subjek_list)
                    jumlah = random.randint(1,5)
                    diterima = random.randint(0,jumlah)
                    detail = DetailDonasi(
                        donasi_id=donasi.id,
                        subjek_id=sub.id,
                        jumlah=jumlah,
                        diterima=diterima,
                        ditolak=jumlah-diterima,
                        kuota=diterima,
                        created_at=get_wib_datetime(),
                        updated_at=get_wib_datetime()
                    )
                    db.session.add(detail)

                print(f"✅ Donasi {invoice} untuk user {user.full_name} berhasil dibuat!")

        db.session.commit()
        print("✅ Semua data dummy Donasi & DetailDonasi berhasil dibuat!")
    except Exception as e:
        print(f"❌ Error membuat dummy donasi: {e}")
        db.session.rollback()

def generate_dummy_data():
    """Generate dummy data untuk KegiatanPerpus, KebutuhanKoleksi, Donasi"""
    try:
        # Generate dummy KegiatanPerpus
        print("📝 Membuat data dummy Kegiatan Perpus...")
        create_dummy_kegiatan_perpus()
        
        # Generate dummy KebutuhanKoleksi
        print("📝 Membuat data dummy Kebutuhan Koleksi...")
        create_dummy_kebutuhan_koleksi()
        
        # Generate dummy Donasi dan DetailDonasi
        print("📝 Membuat data dummy Donasi dan DetailDonasi...")
        create_dummy_donasi()
        
        print("✅ Data dummy berhasil dibuat!")
        
    except Exception as e:
        print(f"❌ Error saat membuat data dummy: {e}")
        db.session.rollback()

def download_sample_image(filename):
    """Download sample image from internet and save to static folder"""
    try:
        # Create directory if not exists
        from flask import current_app
        upload_folder = os.path.join('app', 'static', 'public', 'kegiatan-perpus')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Use Picsum for random images (800x600)
        img_urls = [
            'https://picsum.photos/800/600?random=1',
            'https://picsum.photos/800/600?random=2',
            'https://picsum.photos/800/600?random=3',
            'https://picsum.photos/800/600?random=4',
            'https://picsum.photos/800/600?random=5',
            'https://picsum.photos/800/600?random=6',
            'https://picsum.photos/800/600?random=7',
            'https://picsum.photos/800/600?random=8',
            'https://picsum.photos/800/600?random=9',
            'https://picsum.photos/800/600?random=10'
        ]
        
        # Get random image
        img_index = int(filename.split('_')[1]) - 1
        img_url = img_urls[img_index]
        
        response = requests.get(img_url, timeout=10)
        if response.status_code == 200:
            image_filename = f"{filename}.jpg"
            image_path = os.path.join(upload_folder, image_filename)
            
            with open(image_path, 'wb') as f:
                f.write(response.content)
            
            print(f"  📷 Foto berhasil diunduh: {image_filename}")
            return image_filename
        else:
            print(f"  ❌ Gagal mengunduh foto untuk {filename}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error download foto {filename}: {e}")
        return None