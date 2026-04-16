from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import db, User, PerpusDesa, KebutuhanKoleksi, DetailKebutuhanKoleksi, Kunjungan, DetailPerpus, KegiatanPerpus,\
                       SubjekBuku, RiwayatDistribusi, DetailRiwayatDistribusi, Donasi
from app.utils.session_manager import SessionManager
from sqlalchemy import extract, func
from datetime import datetime, date
import pytz
from functools import wraps
import os
import hashlib
from werkzeug.utils import secure_filename
from flask import current_app, jsonify
from sqlalchemy import inspect, text  # added

bp = Blueprint('admin', __name__)

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SessionManager.is_logged_in('admin'):
            flash("Silakan login sebagai Admin Perpusdes.", "warning")
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_donasi_notes_column():
    """
    Pastikan kolom 'notes' ada pada tabel donasi.
    Jika belum ada (DB lama), tambahkan secara otomatis agar query tidak error.
    Aman untuk dipanggil berulang (idempotent).
    """
    try:
        inspector = inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns('donasi')]
        if 'notes' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE donasi ADD COLUMN notes TEXT"))
            current_app.logger.info("Kolom 'notes' berhasil ditambahkan ke tabel donasi.")
    except Exception as e:
        current_app.logger.error(f"Gagal memastikan kolom notes pada donasi: {e}")

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            nama_perpus = request.form.get('nama_perpus').strip()
            kecamatan = request.form.get('kecamatan').strip()
            desa = request.form.get('desa').strip()
            full_name = request.form.get('full_name').strip()
            username = request.form.get('username').strip()
            email = request.form.get('email').strip()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            agree_terms = request.form.get('agree_terms')
            
            # Validation
            if not agree_terms:
                flash('Anda harus menyetujui syarat dan ketentuan.', 'error')
                return redirect(url_for('admin.register'))
            
            if password != confirm_password:
                flash('Password dan konfirmasi password tidak cocok.', 'error')
                return redirect(url_for('admin.register'))
            
            if len(password) < 6:
                flash('Password minimal 6 karakter.', 'error')
                return redirect(url_for('admin.register'))
            
            # Check if perpustakaan already exists
            existing_perpus = PerpusDesa.query.filter_by(nama=nama_perpus, desa=desa).first()
            if existing_perpus:
                flash(f'Perpustakaan "{nama_perpus}" di desa "{desa}" sudah terdaftar.', 'error')
                return redirect(url_for('admin.register'))
            
            # Check if username already exists
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                flash(f'Username "{username}" sudah digunakan.', 'error')
                return redirect(url_for('admin.register'))
            
            # Check if email already exists
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash(f'Email "{email}" sudah terdaftar.', 'error')
                return redirect(url_for('admin.register'))
            
            # Create new perpustakaan
            perpus = PerpusDesa(
                nama=nama_perpus,
                kecamatan=kecamatan,
                desa=desa
            )
            db.session.add(perpus)
            db.session.flush()  # Get the perpus.id
            
            # Create new admin user
            admin_user = User(
                username=username,
                full_name=full_name,
                email=email,
                role='admin',
                is_active=False,  # Needs verification
                is_verified=False,  # Needs verification
                perpus_id=perpus.id
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            
            db.session.commit()
            
            flash('Pendaftaran berhasil! Silakan tunggu verifikasi dari admin pusat sebelum dapat login.', 'success')
            return redirect(url_for('admin.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat mendaftar: {str(e)}', 'error')
            return redirect(url_for('admin.register'))
    
    return render_template('admin/register_admin.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Clear any other existing sessions to prevent conflicts
    SessionManager.clear_other_sessions('admin')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_user = User.query.filter_by(username=username, role='admin').first()

        if admin_user and admin_user.check_password(password):
            if not admin_user.is_verified:
                flash('Akun Anda belum diverifikasi oleh admin pusat. Silakan tunggu proses verifikasi.', 'warning')
                return redirect(url_for('admin.login'))
            
            if not admin_user.is_active:
                flash('Akun Anda tidak aktif. Silakan hubungi admin pusat.', 'error')
                return redirect(url_for('admin.login'))
            
            user_data = {
                'user_id': admin_user.id,
                'username': admin_user.username,
                'full_name': admin_user.full_name,
                'email': admin_user.email,
                'perpus_id': admin_user.perpus_id,
                'is_verified': admin_user.is_verified
            }
            SessionManager.set_user_session(user_data, 'admin')
            flash("Login berhasil! Selamat datang di dashboard admin.", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Login gagal. Username/password salah.', 'error')
            return redirect(url_for('admin.login'))

    return render_template('admin/login_admin.html')

@bp.route('/logout')
def logout():
    SessionManager.clear_user_session('admin')
    flash("Anda telah berhasil logout.", "success")
    return redirect(url_for('admin.login'))

@bp.route('/dashboard')
@admin_login_required
def dashboard():
    # Get current time in WIB (UTC+7)
    wib_tz = pytz.timezone('Asia/Jakarta')
    now_wib = datetime.now(wib_tz)
    current_date = now_wib.date()  # This will be the current date in WIB
    current_month = now_wib.month
    current_year = now_wib.year
    
    # Get admin's perpus_id from session
    perpus_id = SessionManager.get_current_perpus_id('admin')
    
    # Calculate today's visits for this perpus (will reset to 0 when date changes in WIB)
    total_kunjungan_hari_ini = 0
    if perpus_id:
        total_kunjungan_hari_ini = Kunjungan.query.filter(
            func.date(Kunjungan.tanggal) == current_date,
            Kunjungan.perpus_id == perpus_id
        ).count()
    
    # Calculate this month's visits for this perpus (will reset to 0 when month changes in WIB)
    total_kunjungan_bulan_ini = 0
    if perpus_id:
        total_kunjungan_bulan_ini = Kunjungan.query.filter(
            extract('month', Kunjungan.tanggal) == current_month,
            extract('year', Kunjungan.tanggal) == current_year,
            Kunjungan.perpus_id == perpus_id
        ).count()
    
    # Calculate Kegiatan Tercatat - based on kegiatan_perpus table for this perpus
    total_kegiatan = 0
    if perpus_id:
        total_kegiatan = KegiatanPerpus.query.filter_by(perpus_id=perpus_id).count()
    
    # Calculate Buku dari Perpus Pusat - berdasarkan detail distribusi dengan status 'diterima'
    total_buku_pusat = 0
    if perpus_id:
        total_buku_pusat = db.session.query(func.sum(DetailRiwayatDistribusi.jumlah))\
            .join(RiwayatDistribusi)\
            .filter(
                RiwayatDistribusi.perpus_id == perpus_id,
                RiwayatDistribusi.status == 'diterima'
            ).scalar() or 0

    # Donasi masuk sama dengan itu
    total_donasi_buku = total_buku_pusat
    
    # Calculate percentage increase for collection - berdasarkan perbandingan bulan ini vs bulan lalu
    persentase_kenaikan_koleksi = 0
    if perpus_id:
        # Calculate previous month and year
        if current_month == 1:
            previous_month = 12
            previous_year = current_year - 1
        else:
            previous_month = current_month - 1
            previous_year = current_year
        
        # Calculate books received this month
        buku_bulan_ini = db.session.query(func.sum(DetailRiwayatDistribusi.jumlah))\
            .join(RiwayatDistribusi)\
            .filter(
                RiwayatDistribusi.perpus_id == perpus_id,
                RiwayatDistribusi.status == 'diterima',
                extract('month', RiwayatDistribusi.updated_at) == current_month,
                extract('year', RiwayatDistribusi.updated_at) == current_year
            ).scalar() or 0
        
        # Calculate books received last month
        buku_bulan_lalu = db.session.query(func.sum(DetailRiwayatDistribusi.jumlah))\
            .join(RiwayatDistribusi)\
            .filter(
                RiwayatDistribusi.perpus_id == perpus_id,
                RiwayatDistribusi.status == 'diterima',
                extract('month', RiwayatDistribusi.updated_at) == previous_month,
                extract('year', RiwayatDistribusi.updated_at) == previous_year
            ).scalar() or 0
        
        # Calculate percentage increase
        if buku_bulan_lalu > 0:
            persentase_kenaikan_koleksi = round(((buku_bulan_ini - buku_bulan_lalu) / buku_bulan_lalu) * 100, 1)
        elif buku_bulan_ini > 0:
            # If there were no books last month but there are books this month, it's 100% increase
            persentase_kenaikan_koleksi = 100.0
        else:
            # No books in both months
            persentase_kenaikan_koleksi = 0.0

    # === NOTIFICATIONS ===
    
    # Kebutuhan koleksi menunggu verifikasi - status 'pending'
    koleksi_pending_count = 0
    if perpus_id:
        koleksi_pending_count = KebutuhanKoleksi.query.filter(
            KebutuhanKoleksi.perpus_id == perpus_id,
            KebutuhanKoleksi.status == 'pending'
        ).count()
    
    # Distribusi buku belum dikonfirmasi - status 'pengiriman'
    distribusi_pending_count = 0
    if perpus_id:
        distribusi_pending_count = RiwayatDistribusi.query.filter(
            RiwayatDistribusi.perpus_id == perpus_id,
            RiwayatDistribusi.status == 'pengiriman'
        ).count()
    
    # Check if detail_perpus exists for this perpus_id
    detail_perpus_exists = False
    if perpus_id:
        detail_perpus_exists = DetailPerpus.query.filter_by(perpus_id=perpus_id).first() is not None
    
    # Prepare notification messages
    if koleksi_pending_count > 0:
        notif_koleksi_pending = f"{koleksi_pending_count} kebutuhan koleksi menunggu verifikasi."
    else:
        notif_koleksi_pending = "Tidak ada kebutuhan koleksi yang menunggu verifikasi."
    
    if distribusi_pending_count > 0:
        notif_distribusi_pending = f"{distribusi_pending_count} distribusi buku belum dikonfirmasi."
    else:
        notif_distribusi_pending = "Semua distribusi buku sudah dikonfirmasi."
    
    if not detail_perpus_exists:
        notif_kegiatan_blm_lengkap = "Lengkapi data kegiatan perpustakaan di profil perpustakaan."
    else:
        notif_kegiatan_blm_lengkap = "Data profil perpustakaan sudah lengkap."
    
    # Get month name in Indonesian
    month_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    current_month_name = month_names.get(current_month, 'Unknown')
    
    # Format current date for display in Indonesian
    current_date_formatted = now_wib.strftime('%d %B %Y').replace(
        'January', 'Januari').replace('February', 'Februari').replace('March', 'Maret').replace(
        'April', 'April').replace('May', 'Mei').replace('June', 'Juni').replace(
        'July', 'Juli').replace('August', 'Agustus').replace('September', 'September').replace(
        'October', 'Oktober').replace('November', 'November').replace('December', 'Desember')
    
    return render_template('admin/dashboard.html',
        total_buku_pusat=total_buku_pusat, 
        total_donasi_buku=total_donasi_buku, 
        total_kegiatan=total_kegiatan,
        persentase_kenaikan_koleksi=persentase_kenaikan_koleksi, 
        total_kunjungan_hari_ini=total_kunjungan_hari_ini,
        total_kunjungan_bulan_ini=total_kunjungan_bulan_ini,
        current_month_name=current_month_name,
        current_year=current_year,
        current_date_formatted=current_date_formatted,
        notif_koleksi_pending=notif_koleksi_pending,
        notif_distribusi_pending=notif_distribusi_pending,
        notif_kegiatan_blm_lengkap=notif_kegiatan_blm_lengkap
    )

@bp.route('/profil-perpustakaan', methods=['GET', 'POST'])
@admin_login_required
def profil_perpustakaan():
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get_or_404(user_id)
    perpus = user.perpus
    detail_perpus = DetailPerpus.query.filter_by(perpus_id=user.perpus_id).first()

    if not perpus:
        flash("Akun admin Anda tidak terhubung dengan data perpustakaan.", "error")
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        try:
            # Handle photo upload
            foto_filename = None
            if 'foto' in request.files:
                file = request.files['foto']
                if file and file.filename and allowed_file(file.filename):
                    # Check file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        flash("Ukuran file foto terlalu besar. Maksimal 2MB.", "error")
                        return redirect(url_for('admin.profil_perpustakaan'))
                    
                    # Generate unique filename and save
                    foto_filename = generate_filename(file.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static', 'public', 'foto-perpus')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, foto_filename))

            # Parse time inputs
            jam_mulai = None
            jam_selesai = None
            if request.form.get('jam_operasional_mulai'):
                jam_mulai = datetime.strptime(request.form.get('jam_operasional_mulai'), '%H:%M').time()
            if request.form.get('jam_operasional_selesai'):
                jam_selesai = datetime.strptime(request.form.get('jam_operasional_selesai'), '%H:%M').time()

            # Parse numeric inputs
            jumlah_koleksi = None
            jumlah_eksemplar = None
            
            if request.form.get('jumlah_koleksi') and int(request.form.get('jumlah_koleksi')) >= 0:
                jumlah_koleksi = int(request.form.get('jumlah_koleksi'))
            
            if request.form.get('jumlah_eksemplar') and int(request.form.get('jumlah_eksemplar')) >= 0:
                jumlah_eksemplar = int(request.form.get('jumlah_eksemplar'))

            # Parse GPS coordinates and generate Google Maps link
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            lokasi_link = None
            
            if latitude and longitude:
                lat_float = float(latitude)
                lng_float = float(longitude)
                lokasi_link = f"https://www.google.com/maps?q={lat_float},{lng_float}"

            if detail_perpus:
                # Update existing record
                detail_perpus.penanggung_jawab = request.form.get('penanggung_jawab')
                detail_perpus.deskripsi = request.form.get('deskripsi')
                detail_perpus.latar_belakang = request.form.get('latar_belakang')
                detail_perpus.jumlah_koleksi = jumlah_koleksi
                detail_perpus.jumlah_eksemplar = jumlah_eksemplar
                detail_perpus.jam_operasional_mulai = jam_mulai
                detail_perpus.jam_operasional_selesai = jam_selesai
                detail_perpus.koleksi_buku = request.form.get('koleksi_buku')
                detail_perpus.lokasi = lokasi_link
                detail_perpus.latitude = float(latitude) if latitude else None
                detail_perpus.longitude = float(longitude) if longitude else None
                detail_perpus.updated_at = datetime.now()
                
                if foto_filename:
                    # Delete old photo if exists
                    if detail_perpus.foto_perpus:
                        old_photo_path = os.path.join(current_app.root_path, 'static', 'public', 'foto-perpus', detail_perpus.foto_perpus)
                        if os.path.exists(old_photo_path):
                            os.remove(old_photo_path)
                    detail_perpus.foto_perpus = foto_filename
            else:
                # Create new record
                detail_perpus = DetailPerpus(
                    perpus_id=user.perpus_id,
                    penanggung_jawab=request.form.get('penanggung_jawab'),
                    foto_perpus=foto_filename,
                    deskripsi=request.form.get('deskripsi'),
                    latar_belakang=request.form.get('latar_belakang'),
                    jumlah_koleksi=jumlah_koleksi,
                    jumlah_eksemplar=jumlah_eksemplar,
                    jam_operasional_mulai=jam_mulai,
                    jam_operasional_selesai=jam_selesai,
                    koleksi_buku=request.form.get('koleksi_buku'),
                    lokasi=lokasi_link,
                    latitude=float(latitude) if latitude else None,
                    longitude=float(longitude) if longitude else None
                )
                db.session.add(detail_perpus)

            db.session.commit()
            flash("Data profil perpustakaan berhasil disimpan!", "success")
            return redirect(url_for('admin.profil_perpustakaan'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Terjadi kesalahan: {str(e)}", "error")
            return redirect(url_for('admin.profil_perpustakaan'))

    return render_template('admin/profil_perpustakaan.html', 
                         perpus=perpus, 
                         admin=user, 
                         detail_perpus=detail_perpus)

@bp.route('/kebutuhan-koleksi', methods=['GET', 'POST'])
@admin_login_required
def kebutuhan_koleksi():
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    perpus = user.perpus
    detail_perpus = DetailPerpus.query.filter_by(perpus_id=user.perpus_id).first()
    
    if request.method == 'POST':
        # Check if profile is complete before processing form
        if not detail_perpus or not detail_perpus.penanggung_jawab or not detail_perpus.deskripsi or not detail_perpus.lokasi:
            flash("Silakan lengkapi profil perpustakaan terlebih dahulu sebelum mengajukan kebutuhan koleksi.", "warning")
            return redirect(url_for('admin.profil_perpustakaan'))
        
        kebutuhan_id = request.form.get('kebutuhan_id')
        
        if kebutuhan_id:  # Update existing
            kebutuhan = KebutuhanKoleksi.query.get_or_404(kebutuhan_id)
            if kebutuhan.perpus_id != user.perpus_id:
                flash("Anda tidak memiliki akses untuk mengedit data ini.", "error")
                return redirect(url_for('admin.kebutuhan_koleksi'))
            
            # Update main kebutuhan record
            kebutuhan.prioritas = request.form.get('prioritas')
            kebutuhan.lokasi = request.form.get('lokasi')
            kebutuhan.alasan = request.form.get('alasan')
            kebutuhan.updated_at = datetime.now(pytz.timezone('Asia/Jakarta'))
            
            # Update details - first delete existing details
            DetailKebutuhanKoleksi.query.filter_by(kebutuhan_id=kebutuhan.id).delete()
            
            # Add new details
            subjek_ids = request.form.getlist('subjek_id[]')
            jumlah_bukus = request.form.getlist('jumlah_buku[]')
            
            for subjek_id, jumlah_buku in zip(subjek_ids, jumlah_bukus):
                if subjek_id and jumlah_buku:
                    detail = DetailKebutuhanKoleksi(
                        kebutuhan_id=kebutuhan.id,
                        subjek_id=int(subjek_id),
                        jumlah_buku=int(jumlah_buku),
                        created_at=datetime.now(pytz.timezone('Asia/Jakarta')),
                        updated_at=datetime.now(pytz.timezone('Asia/Jakarta'))
                    )
                    db.session.add(detail)
            
            flash("Data kebutuhan koleksi berhasil diperbarui.", "success")
        else:  # Create new
            kebutuhan = KebutuhanKoleksi(
                perpus_id=user.perpus_id,
                prioritas=request.form.get('prioritas'),
                lokasi=request.form.get('lokasi'),
                alasan=request.form.get('alasan'),
                status='pending',  # New requests always start as pending
            )
            db.session.add(kebutuhan)
            db.session.flush()  # Get the kebutuhan.id
            
            # Add details
            subjek_ids = request.form.getlist('subjek_id[]')
            jumlah_bukus = request.form.getlist('jumlah_buku[]')
            
            for subjek_id, jumlah_buku in zip(subjek_ids, jumlah_bukus):
                if subjek_id and jumlah_buku:
                    detail = DetailKebutuhanKoleksi(
                        kebutuhan_id=kebutuhan.id,
                        subjek_id=int(subjek_id),
                        jumlah_buku=int(jumlah_buku)
                    )
                    db.session.add(detail)
            
            flash("Pengajuan kebutuhan koleksi berhasil dikirim.", "success")
        
        db.session.commit()
        return redirect(url_for('admin.kebutuhan_koleksi'))
    
    # GET request - show page with data
    data_kebutuhan = KebutuhanKoleksi.query.filter_by(perpus_id=user.perpus_id).order_by(KebutuhanKoleksi.tanggal_pengajuan.desc()).all()
    subjek_list = SubjekBuku.query.order_by(SubjekBuku.nama).all()
    
    return render_template('admin/kebutuhan_koleksi.html', 
                         data_kebutuhan=data_kebutuhan,
                         perpus=perpus,
                         detail_perpus=detail_perpus,
                         subjek_list=subjek_list)

@bp.route('/kebutuhan-koleksi/<int:id>/edit', methods=['GET'])
@admin_login_required
def edit_kebutuhan_koleksi(id):
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    kebutuhan = KebutuhanKoleksi.query.get_or_404(id)
    
    if kebutuhan.perpus_id != user.perpus_id:
        return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
    
    try:
        # Format tanggal pengajuan properly
        tanggal_formatted = kebutuhan.tanggal_pengajuan.strftime('%Y-%m-%d') if kebutuhan.tanggal_pengajuan else None
        
        # Get details
        details = []
        for detail in kebutuhan.detail_kebutuhan:
            details.append({
                'subjek_id': detail.subjek_id,
                'subjek_nama': detail.subjek.nama,
                'jumlah_buku': detail.jumlah_buku
            })
        
        return jsonify({
            'success': True,
            'data': {
                'id': kebutuhan.id,
                'perpus_nama': kebutuhan.perpus.nama,
                'prioritas': kebutuhan.prioritas,
                'lokasi': kebutuhan.lokasi,
                'alasan': kebutuhan.alasan,
                'pesan': kebutuhan.pesan,
                'status': kebutuhan.status,
                'tanggal_pengajuan': tanggal_formatted,
                'details': details
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@bp.route('/kegiatan-perpus', methods=['GET', 'POST'])
@admin_login_required
def kegiatan_perpus():
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        kegiatan_id = request.form.get('kegiatan_id')
        
        try:
            # Handle photo upload
            foto_filename = None
            if 'foto_kegiatan' in request.files:
                file = request.files['foto_kegiatan']
                if file and file.filename and allowed_file(file.filename):
                    # Check file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        flash("Ukuran file foto terlalu besar. Maksimal 2MB.", "error")
                        return redirect(url_for('admin.kegiatan_perpus'))
                    
                    # Generate unique filename and save
                    foto_filename = generate_filename(file.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static', 'public', 'kegiatan-perpus')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, foto_filename))

            # Parse date
            tanggal_kegiatan = datetime.strptime(request.form.get('tanggal_kegiatan'), '%Y-%m-%d').date()
            
            # Parse GPS coordinates and generate Google Maps link
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            lokasi_link = request.form.get('lokasi_kegiatan')  # Use the form field directly
            
            # If coordinates are provided, ensure we have a proper Google Maps link
            if latitude and longitude:
                lat_float = float(latitude)
                lng_float = float(longitude)
                if not lokasi_link or not lokasi_link.startswith('https://www.google.com/maps'):
                    lokasi_link = f"https://www.google.com/maps?q={lat_float},{lng_float}"

            if kegiatan_id:  # Update existing
                kegiatan = KegiatanPerpus.query.get_or_404(kegiatan_id)
                if kegiatan.perpus_id != user.perpus_id:
                    flash("Anda tidak memiliki akses untuk mengedit data ini.", "error")
                    return redirect(url_for('admin.kegiatan_perpus'))
                
                kegiatan.nama_kegiatan = request.form.get('nama_kegiatan')
                kegiatan.tanggal_kegiatan = tanggal_kegiatan
                kegiatan.deskripsi_kegiatan = request.form.get('deskripsi_kegiatan')
                kegiatan.lokasi_kegiatan = lokasi_link
                kegiatan.latitude = float(latitude) if latitude else None
                kegiatan.longitude = float(longitude) if longitude else None
                kegiatan.status = request.form.get('status', 'active')
                kegiatan.updated_at = datetime.now(pytz.timezone('Asia/Jakarta'))
                
                if foto_filename:
                    # Delete old photo if exists
                    if kegiatan.foto_kegiatan:
                        old_photo_path = os.path.join(current_app.root_path, 'static', 'public', 'kegiatan-perpus', kegiatan.foto_kegiatan)
                        if os.path.exists(old_photo_path):
                            os.remove(old_photo_path)
                    kegiatan.foto_kegiatan = foto_filename
                
                flash("Data kegiatan berhasil diperbarui.", "success")
            else:  # Create new
                kegiatan = KegiatanPerpus(
                    user_id=user.id,  # Add the required user_id field
                    perpus_id=user.perpus_id,
                    nama_kegiatan=request.form.get('nama_kegiatan'),
                    tanggal_kegiatan=tanggal_kegiatan,
                    deskripsi_kegiatan=request.form.get('deskripsi_kegiatan'),
                    lokasi_kegiatan=lokasi_link,
                    latitude=float(latitude) if latitude else None,
                    longitude=float(longitude) if longitude else None,
                    foto_kegiatan=foto_filename,
                    status='active'
                )
                db.session.add(kegiatan)
                flash("Data kegiatan berhasil disimpan.", "success")
            
            db.session.commit()
            
        except ValueError as e:
            db.session.rollback()
            flash(f"Format data tidak valid: {str(e)}", "error")
        except Exception as e:
            db.session.rollback()
            flash(f"Terjadi kesalahan: {str(e)}", "error")
        
        return redirect(url_for('admin.kegiatan_perpus'))
    
    # GET request - show page with data
    data_kegiatan = KegiatanPerpus.query.filter_by(perpus_id=user.perpus_id).order_by(KegiatanPerpus.tanggal_kegiatan.desc()).all()
    
    return render_template('admin/kegiatan_perpus.html', data_kegiatan=data_kegiatan)

@bp.route('/kegiatan-perpus/<int:id>/edit', methods=['GET'])
@admin_login_required
def edit_kegiatan_perpus(id):
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    kegiatan = KegiatanPerpus.query.get_or_404(id)
    
    if kegiatan.perpus_id != user.perpus_id:
        return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
    
    try:
        return jsonify({
            'success': True,
            'data': {
                'id': kegiatan.id,
                'nama_kegiatan': kegiatan.nama_kegiatan,
                'tanggal_kegiatan': kegiatan.tanggal_kegiatan.strftime('%Y-%m-%d'),
                'deskripsi_kegiatan': kegiatan.deskripsi_kegiatan,
                'lokasi_kegiatan': kegiatan.lokasi_kegiatan,
                'latitude': kegiatan.latitude,
                'longitude': kegiatan.longitude,
                'foto_kegiatan': kegiatan.foto_kegiatan,
                'status': kegiatan.status
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@bp.route('/kegiatan-perpus/<int:id>/detail', methods=['GET'])
@admin_login_required
def detail_kegiatan_perpus(id):
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    kegiatan = KegiatanPerpus.query.get_or_404(id)
    
    if kegiatan.perpus_id != user.perpus_id:
        return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
    
    try:
        return jsonify({
            'success': True,
            'data': {
                'id': kegiatan.id,
                'nama_kegiatan': kegiatan.nama_kegiatan,
                'tanggal_kegiatan': kegiatan.tanggal_kegiatan.strftime('%Y-%m-%d'),
                'deskripsi_kegiatan': kegiatan.deskripsi_kegiatan,
                'lokasi_kegiatan': kegiatan.lokasi_kegiatan,
                'latitude': kegiatan.latitude,
                'longitude': kegiatan.longitude,
                'foto_kegiatan': kegiatan.foto_kegiatan,
                'status': kegiatan.status
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@bp.route('/kegiatan-perpus/<int:id>/delete', methods=['DELETE'])
@admin_login_required
def delete_kegiatan_perpus(id):
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    kegiatan = KegiatanPerpus.query.get_or_404(id)
    
    if kegiatan.perpus_id != user.perpus_id:
        return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
    
    try:
        # Delete photo file if exists
        if kegiatan.foto_kegiatan:
            photo_path = os.path.join(current_app.root_path, 'static', 'public', 'kegiatan-perpus', kegiatan.foto_kegiatan)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        
        db.session.delete(kegiatan)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Data berhasil dihapus'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

@bp.route('/kunjungan-analytics')
@admin_login_required
def kunjungan_analytics():
    perpus_id = SessionManager.get_current_perpus_id('admin')
    
    # Get current time in WIB (UTC+7)
    wib_tz = pytz.timezone('Asia/Jakarta')
    now_wib = datetime.now(wib_tz)
    current_year = now_wib.year
    
    # Get available years from kunjungan data for this perpus
    available_years = []
    if perpus_id:
        years_query = db.session.query(extract('year', Kunjungan.tanggal).label('year')).filter(
            Kunjungan.perpus_id == perpus_id
        ).distinct().order_by(extract('year', Kunjungan.tanggal).desc()).all()
        
        available_years = [int(year[0]) for year in years_query]
        
        # Add current year if no data exists yet
        if not available_years or current_year not in available_years:
            available_years.insert(0, current_year)
    else:
        available_years = [current_year]
    
    return render_template('admin/kunjungan_analytics.html', 
                         available_years=available_years,
                         current_year=current_year,
                         perpus_id=perpus_id)

@bp.route('/api/kunjungan-data/<int:year>')
@admin_login_required
def api_kunjungan_data(year):
    perpus_id = SessionManager.get_current_perpus_id('admin')
    
    if not perpus_id:
        return jsonify({'error': 'Data perpustakaan tidak ditemukan'}), 404
    
    try:
        # Get monthly data for the specified year
        monthly_data = []
        total_visits = 0
        
        for month in range(1, 13):
            count = Kunjungan.query.filter(
                extract('month', Kunjungan.tanggal) == month,
                extract('year', Kunjungan.tanggal) == year,
                Kunjungan.perpus_id == perpus_id
            ).count()
            
            monthly_data.append({
                'month': month,
                'count': count
            })
            total_visits += count
        
        return jsonify({
            'data': monthly_data,
            'total': total_visits,
            'year': year
        })
        
    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500

@bp.route('/tambah-kunjungan', methods=['POST'])
@admin_login_required
def tambah_kunjungan():
    perpus_id = SessionManager.get_current_perpus_id('admin')
    
    if perpus_id:
        wib_tz = pytz.timezone('Asia/Jakarta')
        current_time = datetime.now(wib_tz)  # Store in WIB timezone
        
        kunjungan = Kunjungan(
            perpus_id=perpus_id,
            tanggal=current_time
        )
        db.session.add(kunjungan)
        db.session.commit()
        flash("Kunjungan berhasil ditambahkan.", "success")
    else:
        flash("Error: Data perpustakaan tidak ditemukan.", "error")
    
    return redirect(url_for('admin.dashboard'))

@bp.route('/kurangi-kunjungan', methods=['POST'])
@admin_login_required
def kurangi_kunjungan():
    perpus_id = SessionManager.get_current_perpus_id('admin')
    
    if perpus_id:
        wib_tz = pytz.timezone('Asia/Jakarta')
        current_date = datetime.now(wib_tz).date()  # Get current date in WIB
        
        # Find the most recent visit for today (WIB date)
        kunjungan = Kunjungan.query.filter(
            func.date(Kunjungan.tanggal) == current_date,
            Kunjungan.perpus_id == perpus_id
        ).order_by(Kunjungan.tanggal.desc()).first()
        
        if kunjungan:
            db.session.delete(kunjungan)
            db.session.commit()
            flash("Kunjungan berhasil dikurangi.", "success")
        else:
            flash("Tidak ada kunjungan hari ini untuk dikurangi.", "warning")
    else:
        flash("Error: Data perpustakaan tidak ditemukan.", "error")
    
    return redirect(url_for('admin.dashboard'))

@bp.route('/riwayat-distribusi', methods=['GET', 'POST'])
@admin_login_required
def riwayat_distribusi():
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        distribusi_id = request.form.get('distribusi_id')
        distribusi = RiwayatDistribusi.query.get_or_404(distribusi_id)
        
        if distribusi.perpus_id != user.perpus_id:
            flash("Anda tidak memiliki akses untuk mengedit data ini.", "error")
            return redirect(url_for('admin.riwayat_distribusi'))
        
        try:
            # Handle photo upload
            bukti_filename = None
            if 'bukti_foto' in request.files:
                file = request.files['bukti_foto']
                if file and file.filename and allowed_file(file.filename):
                    # Check file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        flash("Ukuran file foto terlalu besar. Maksimal 2MB.", "error")
                        return redirect(url_for('admin.riwayat_distribusi'))
                    
                    # Generate unique filename and save
                    bukti_filename = generate_filename(file.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static', 'public', 'bukti-distribusi')
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, bukti_filename))
                    
                    # Delete old photo if exists
                    if distribusi.bukti_foto:
                        old_photo_path = os.path.join(upload_folder, distribusi.bukti_foto)
                        if os.path.exists(old_photo_path):
                            os.remove(old_photo_path)
                    
                    distribusi.bukti_foto = bukti_filename
            
            # Update status
            status = request.form.get('status')
            if status in ['pengiriman', 'diterima']:
                distribusi.status = status
            
            distribusi.updated_at = datetime.now(pytz.timezone('Asia/Jakarta'))
            db.session.commit()
            
            flash("Data riwayat distribusi berhasil diperbarui.", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Terjadi kesalahan: {str(e)}", "error")
        
        return redirect(url_for('admin.riwayat_distribusi'))
    
    # GET request - show page with data
    data_distribusi = RiwayatDistribusi.query.filter_by(perpus_id=user.perpus_id).order_by(RiwayatDistribusi.created_at.desc()).all()
    
    return render_template('admin/riwayat_distribusi.html', data_distribusi=data_distribusi)

@bp.route('/riwayat-distribusi/<int:id>/edit', methods=['GET'])
@admin_login_required
def edit_riwayat_distribusi(id):
    ensure_donasi_notes_column()  # ensure schema
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    
    try:
        distribusi = RiwayatDistribusi.query.get_or_404(id)
        
        if distribusi.perpus_id != user.perpus_id:
            return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
        
        # Safely get details with proper error handling
        details = distribusi.detail_riwayat_distribusi or []
        
        # Initialize default values
        invoice = ''
        detail_paket = []
        total_keseluruhan = 0
        
        # Get data from details with safety checks
        if details:
            try:
                first_detail = details[0]
                
                # Safely get invoice
                if hasattr(first_detail, 'donasi') and first_detail.donasi:
                    invoice = getattr(first_detail.donasi, 'invoice', '') or ''
                
                # Group subjects by name and sum their quantities
                subjek_groups = {}
                
                for detail in details:
                    if hasattr(detail, 'subjek') and detail.subjek and hasattr(detail, 'jumlah'):
                        subjek_nama = getattr(detail.subjek, 'nama', '') or 'Subjek Tidak Diketahui'
                        jumlah = getattr(detail, 'jumlah', 0) or 0
                        
                        # Group by subject name
                        if subjek_nama in subjek_groups:
                            subjek_groups[subjek_nama] += jumlah
                        else:
                            subjek_groups[subjek_nama] = jumlah
                        
                        total_keseluruhan += jumlah
                
                # Convert grouped data to list format
                for subjek_nama, total_jumlah in subjek_groups.items():
                    detail_paket.append({
                        'subjek': subjek_nama,
                        'jumlah': total_jumlah
                    })
                
                # Sort by subject name for consistent display
                detail_paket.sort(key=lambda x: x['subjek'])
                
            except (AttributeError, IndexError) as e:
                current_app.logger.warning(f'Error accessing detail relationships: {str(e)}')
        
        # Safely get perpus name
        perpus_nama = ''
        if hasattr(distribusi, 'perpus') and distribusi.perpus:
            perpus_nama = getattr(distribusi.perpus, 'nama', '') or ''
        
        return jsonify({
            'success': True,
            'data': {
                'id': distribusi.id,
                'invoice': invoice,
                'perpus_nama': perpus_nama,
                'detail_paket': detail_paket,
                'total_keseluruhan': total_keseluruhan,
                'status': distribusi.status or 'pengiriman',
                'bukti_foto': distribusi.bukti_foto,
                'created_at': distribusi.created_at.strftime('%d-%m-%Y') if distribusi.created_at else ''
            }
        })
    except Exception as e:
        current_app.logger.error(f'Error in edit_riwayat_distribusi for id {id}: {str(e)}')
        current_app.logger.error(f'Error type: {type(e).__name__}')
        import traceback
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'Terjadi kesalahan server: {str(e)}'}), 500

@bp.route('/riwayat-distribusi/<int:id>/detail', methods=['GET'])
@admin_login_required
def detail_riwayat_distribusi(id):
    ensure_donasi_notes_column()  # ensure schema
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    
    try:
        distribusi = RiwayatDistribusi.query.get_or_404(id)
        
        if distribusi.perpus_id != user.perpus_id:
            return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
        
        # Safely get details with proper error handling
        details = distribusi.detail_riwayat_distribusi or []
        
        # Initialize default values
        invoice = ''
        detail_paket = []
        total_keseluruhan = 0
        
        # Get data from details with safety checks
        if details:
            try:
                first_detail = details[0]
                
                # Safely get invoice
                if hasattr(first_detail, 'donasi') and first_detail.donasi:
                    invoice = getattr(first_detail.donasi, 'invoice', '') or ''
                
                # Group subjects by name and sum their quantities
                subjek_groups = {}
                
                for detail in details:
                    if hasattr(detail, 'subjek') and detail.subjek and hasattr(detail, 'jumlah'):
                        subjek_nama = getattr(detail.subjek, 'nama', '') or 'Subjek Tidak Diketahui'
                        jumlah = getattr(detail, 'jumlah', 0) or 0
                        
                        # Group by subject name
                        if subjek_nama in subjek_groups:
                            subjek_groups[subjek_nama] += jumlah
                        else:
                            subjek_groups[subjek_nama] = jumlah
                        
                        total_keseluruhan += jumlah
                
                # Convert grouped data to list format
                for subjek_nama, total_jumlah in subjek_groups.items():
                    detail_paket.append({
                        'subjek': subjek_nama,
                        'jumlah': total_jumlah
                    })
                
                # Sort by subject name for consistent display
                detail_paket.sort(key=lambda x: x['subjek'])
                
            except (AttributeError, IndexError) as e:
                current_app.logger.warning(f'Error accessing detail relationships: {str(e)}')
        
        # Safely get perpus name
        perpus_nama = ''
        if hasattr(distribusi, 'perpus') and distribusi.perpus:
            perpus_nama = getattr(distribusi.perpus, 'nama', '') or ''
        
        return jsonify({
            'success': True,
            'data': {
                'id': distribusi.id,
                'invoice': invoice,
                'perpus_nama': perpus_nama,
                'detail_paket': detail_paket,
                'total_keseluruhan': total_keseluruhan,
                'status': distribusi.status or 'pengiriman',
                'bukti_foto': distribusi.bukti_foto,
                'created_at': distribusi.created_at.strftime('%d-%m-%Y') if distribusi.created_at else ''
            }
        })
    except Exception as e:
        current_app.logger.error(f'Error in detail_riwayat_distribusi for id {id}: {str(e)}')
        current_app.logger.error(f'Error type: {type(e).__name__}')
        import traceback
        current_app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({'success': False, 'message': f'Terjadi kesalahan server: {str(e)}'}), 500

@bp.route('/kebutuhan-koleksi/<int:id>/delete', methods=['DELETE'])
@admin_login_required
def delete_kebutuhan_koleksi(id):
    user_id = SessionManager.get_current_user_id('admin')
    user = User.query.get(user_id)
    kebutuhan = KebutuhanKoleksi.query.get_or_404(id)
    
    if kebutuhan.perpus_id != user.perpus_id:
        return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
    
    try:
        # Delete related details first
        DetailKebutuhanKoleksi.query.filter_by(kebutuhan_id=kebutuhan.id).delete()
        
        # Delete main record
        db.session.delete(kebutuhan)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data berhasil dihapus'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_filename(original_filename):
    """Generate a unique hashed filename"""
    timestamp = str(datetime.now().timestamp())
    extension = original_filename.rsplit('.', 1)[1].lower()
    hash_input = f"{original_filename}{timestamp}".encode('utf-8')
    hash_name = hashlib.md5(hash_input).hexdigest()
    return f"{hash_name}.{extension}"