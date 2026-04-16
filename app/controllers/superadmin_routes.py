from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app.models import db, User, PerpusDesa, DetailDonasi, Donasi, KebutuhanKoleksi, DetailKebutuhanKoleksi, DetailPerpus, SubjekBuku, RiwayatDistribusi, DetailRiwayatDistribusi, Kunjungan
from app.utils.session_manager import SessionManager
from app.utils.email_utils import EmailService
from sqlalchemy import func, case
from sqlalchemy.orm import joinedload
from functools import wraps
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import hashlib

bp = Blueprint('superadmin', __name__)

def superadmin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SessionManager.is_logged_in('superadmin'):
            flash("Akses ditolak. Anda bukan superadmin.", "danger")
            return redirect(url_for('superadmin.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, role='superadmin').first()

        if user and user.check_password(password):
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'perpus_id': user.perpus_id,
                'is_verified': user.is_verified
            }
            SessionManager.set_user_session(user_data, 'superadmin')
            return redirect(url_for('superadmin.dashboard'))
        else:
            flash("Login gagal. Username atau password salah.", "error")
    return render_template('superadmin/login.html')

@bp.route('/dashboard')
@superadmin_login_required
def dashboard():
    # Count unique donators with status 'confirmed' only
    total_donatur = db.session.query(Donasi.user_id)\
        .filter(Donasi.status == 'confirmed')\
        .distinct().count()
    
    # Count total books from donations with status 'confirmed' only
    total_buku = db.session.query(func.sum(DetailDonasi.jumlah))\
        .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
        .filter(Donasi.status == 'confirmed')\
        .scalar() or 0
    
    total_perpus = PerpusDesa.query.count()
    
    # Get pending kebutuhan koleksi with perpus info and calculate total books
    permintaan_list = db.session.query(KebutuhanKoleksi)\
        .options(joinedload(KebutuhanKoleksi.perpus),
                joinedload(KebutuhanKoleksi.detail_kebutuhan))\
        .filter(KebutuhanKoleksi.status == 'pending')\
        .order_by(
            case(
                (KebutuhanKoleksi.prioritas == 'tinggi', 1),
                (KebutuhanKoleksi.prioritas == 'sedang', 2),
                (KebutuhanKoleksi.prioritas == 'rendah', 3),
                else_=4
            ),
            KebutuhanKoleksi.tanggal_pengajuan.desc()
        ).limit(5).all()

    # Calculate total books for each kebutuhan
    for kebutuhan in permintaan_list:
        kebutuhan.total_buku = sum(detail.jumlah_buku for detail in kebutuhan.detail_kebutuhan)

    riwayat_donasi_raw = db.session.query(
        SubjekBuku.nama.label('subjek'),
        DetailDonasi.jumlah,
        User.full_name.label('nama')
    )\
     .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
     .join(User, User.id == Donasi.user_id)\
     .join(SubjekBuku, SubjekBuku.id == DetailDonasi.subjek_id)\
     .filter(Donasi.status == 'confirmed')\
     .order_by(Donasi.created_at.desc())\
     .limit(5).all()

    riwayat_donasi = [{
        'subjek': item.subjek,
        'jumlah': item.jumlah,
        'donatur': {'full_name': item.nama}
    } for item in riwayat_donasi_raw]

    return render_template('superadmin/tampilan_depan.html',
                           total_donatur=total_donatur,
                           total_buku=total_buku,
                           total_perpus=total_perpus,
                           permintaan_list=permintaan_list,
                           riwayat_donasi=riwayat_donasi)

@bp.route('/perpusdes')
@superadmin_login_required
def daftar_perpustakaan():
    # Use LEFT JOIN to include all libraries, even those without admin users
    data_perpus = db.session.query(PerpusDesa, User).outerjoin(User, User.perpus_id == PerpusDesa.id).order_by(PerpusDesa.id.asc()).all()
    return render_template('superadmin/perpusdesa.html', data_perpus=data_perpus)

@bp.route('/tambah-perpustakaan', methods=['GET', 'POST'])
@superadmin_login_required
def tambah_perpustakaan():
    if request.method == 'POST':
        try:
            nama_perpus = request.form['nama_perpus']
            kecamatan = request.form['kecamatan']
            desa = request.form['desa']
            username = request.form['username']
            password = request.form['password']

            if PerpusDesa.query.filter_by(nama=nama_perpus, desa=desa).first():
                return jsonify({'success': False, 'message': f"Perpustakaan '{nama_perpus}' di desa '{desa}' sudah ada."})
            
            if User.query.filter_by(username=username).first():
                return jsonify({'success': False, 'message': f"Username '{username}' sudah digunakan."})

            perpus = PerpusDesa(nama=nama_perpus, kecamatan=kecamatan, desa=desa)
            db.session.add(perpus)
            db.session.flush()

            admin_user = User(
                username=username,
                full_name=f"Admin {nama_perpus}",
                email=f"{username}@perpusdes.id",
                role='admin',
                is_verified=True,
                perpus_id=perpus.id
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Data perpustakaan dan admin baru berhasil ditambahkan.'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Gagal menyimpan data: {str(e)}'})
        
    return render_template('superadmin/tambah_perpustakaan.html')

@bp.route('/verifikasi-admin')
@superadmin_login_required
def verifikasi_admin():
    daftar_admin = User.query.filter_by(role='admin', is_verified=False).all()
    return render_template('superadmin/verifikasi_admin.html', daftar_admin=daftar_admin)

@bp.route('/admin/detail/<int:admin_id>')
@superadmin_login_required
def detail_admin(admin_id):
    admin_user = User.query.get_or_404(admin_id)
    
    # Make sure this is an admin role
    if admin_user.role != 'admin':
        return jsonify({'success': False, 'message': 'User bukan admin'})
    
    try:
        admin_data = {
            'id': admin_user.id,
            'full_name': admin_user.full_name,
            'username': admin_user.username,
            'email': admin_user.email,
            'created_at': admin_user.created_at.strftime('%d/%m/%Y %H:%M') if admin_user.created_at else None,
            'is_active': admin_user.is_active,
            'is_verified': admin_user.is_verified
        }
        
        perpus_data = None
        if admin_user.perpus:
            perpus_data = {
                'id': admin_user.perpus.id,
                'nama': admin_user.perpus.nama,
                'kecamatan': admin_user.perpus.kecamatan,
                'desa': admin_user.perpus.desa,
                'created_at': admin_user.perpus.created_at.strftime('%d/%m/%Y %H:%M') if admin_user.perpus.created_at else None
            }
        else:
            perpus_data = {
                'nama': 'Belum ditentukan',
                'kecamatan': '-',
                'desa': '-',
                'created_at': '-'
            }
        
        return jsonify({
            'success': True,
            'admin': admin_data,
            'perpus': perpus_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'})

@bp.route('/verifikasi-admin/proses/<int:user_id>', methods=['GET', 'POST'])
@superadmin_login_required
def verifikasi_admin_proses(user_id):
    admin_user = User.query.get_or_404(user_id)
    
    # Update both is_active and is_verified to True
    admin_user.is_active = True
    admin_user.is_verified = True
    db.session.commit()
    
    if request.method == 'POST':
        # AJAX request
        return jsonify({'success': True, 'message': f"Admin '{admin_user.username}' berhasil diverifikasi dan diaktifkan."})
    else:
        # Regular GET request (fallback)
        flash(f"Admin '{admin_user.username}' berhasil diverifikasi dan diaktifkan.", "success")
        return redirect(url_for('superadmin.verifikasi_admin'))

@bp.route('/logout')
@superadmin_login_required
def logout():
    SessionManager.clear_user_session('superadmin')
    flash("Anda telah berhasil logout.", "success")
    return redirect(url_for('superadmin.login'))

@bp.route('/perpusdes/detail/<int:perpus_id>')
@superadmin_login_required
def detail_perpustakaan(perpus_id):
    perpus = PerpusDesa.query.get_or_404(perpus_id)
    admin = User.query.filter_by(perpus_id=perpus_id).first()
    detail_perpus = DetailPerpus.query.filter_by(perpus_id=perpus_id).first()
    
    return render_template('superadmin/partials/detail_perpus.html', 
                         perpus=perpus, admin=admin, detail_perpus=detail_perpus)

@bp.route('/perpusdes/edit/<int:perpus_id>')
@superadmin_login_required
def edit_perpustakaan_form(perpus_id):
    perpus = PerpusDesa.query.get_or_404(perpus_id)
    admin = User.query.filter_by(perpus_id=perpus_id).first()
    
    return render_template('superadmin/partials/edit_perpus.html', 
                         perpus=perpus, admin=admin)

@bp.route('/perpusdes/update/<int:perpus_id>', methods=['POST'])
@superadmin_login_required
def update_perpustakaan(perpus_id):
    try:
        perpus = PerpusDesa.query.get_or_404(perpus_id)
        admin = User.query.filter_by(perpus_id=perpus_id).first()
        
        # Update perpustakaan data
        perpus.nama = request.form.get('nama_perpus')
        perpus.kecamatan = request.form.get('kecamatan')
        perpus.desa = request.form.get('desa')
        
        # Update admin data
        if admin:
            new_username = request.form.get('username')
            if new_username != admin.username:
                # Check if new username already exists
                existing_user = User.query.filter_by(username=new_username).first()
                if existing_user and existing_user.id != admin.id:
                    return jsonify({'success': False, 'message': f'Username "{new_username}" sudah digunakan.'})
                admin.username = new_username
            
            admin.full_name = request.form.get('full_name', f"Admin {perpus.nama}")
            
            # Update password if provided
            new_password = request.form.get('password')
            if new_password:
                admin.set_password(new_password)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Data perpustakaan berhasil diupdate.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal mengupdate data: {str(e)}'})

@bp.route('/perpusdes/delete/<int:perpus_id>', methods=['DELETE'])
@superadmin_login_required
def delete_perpustakaan(perpus_id):
    try:
        perpus = PerpusDesa.query.get_or_404(perpus_id)
        
        # Delete associated admin user
        admin = User.query.filter_by(perpus_id=perpus_id).first()
        if admin:
            db.session.delete(admin)
        
        # Delete associated detail_perpus
        detail_perpus = DetailPerpus.query.filter_by(perpus_id=perpus_id).first()
        if detail_perpus:
            db.session.delete(detail_perpus)
        
        # Delete kebutuhan_koleksi records
        kebutuhan_list = KebutuhanKoleksi.query.filter_by(perpus_id=perpus_id).all()
        for kebutuhan in kebutuhan_list:
            db.session.delete(kebutuhan)
        
        # Delete the perpustakaan
        db.session.delete(perpus)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Perpustakaan "{perpus.nama}" berhasil dihapus.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menghapus perpustakaan: {str(e)}'})

@bp.route('/perpusdes/create-admin/<int:perpus_id>', methods=['POST'])
@superadmin_login_required
def create_admin_for_library(perpus_id):
    try:
        perpus = PerpusDesa.query.get_or_404(perpus_id)
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(perpus_id=perpus_id).first()
        if existing_admin:
            return jsonify({'success': False, 'message': 'Perpustakaan ini sudah memiliki admin.'})
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': f'Username "{username}" sudah digunakan.'})
        
        # Create new admin user
        admin_user = User(
            username=username,
            full_name=f"Admin {perpus.nama}",
            email=f"{username}@perpusdes.id",
            role='admin',
            is_verified=True,
            perpus_id=perpus.id
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Admin untuk "{perpus.nama}" berhasil dibuat.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal membuat admin: {str(e)}'})

@bp.route('/kelola-subjek')
@superadmin_login_required
def kelola_subjek():
    subjek_list = SubjekBuku.query.order_by(SubjekBuku.id.asc()).all()
    return render_template('superadmin/kelola_subjek.html', subjek_list=subjek_list)

@bp.route('/tambah-subjek', methods=['POST'])
@superadmin_login_required
def tambah_subjek():
    try:
        nama_subjek = request.form.get('nama_subjek')
        
        # Check if subject already exists
        if SubjekBuku.query.filter_by(nama=nama_subjek).first():
            return jsonify({'success': False, 'message': f'Subjek "{nama_subjek}" sudah ada.'})
        
        # Create new subject
        subjek = SubjekBuku(nama=nama_subjek)
        db.session.add(subjek)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Subjek "{nama_subjek}" berhasil ditambahkan.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menyimpan subjek: {str(e)}'})

@bp.route('/subjek/edit/<int:subjek_id>')
@superadmin_login_required
def edit_subjek_form(subjek_id):
    subjek = SubjekBuku.query.get_or_404(subjek_id)
    return jsonify({
        'success': True, 
        'subjek': {
            'id': subjek.id,
            'nama': subjek.nama
        }
    })

@bp.route('/subjek/update/<int:subjek_id>', methods=['POST'])
@superadmin_login_required
def update_subjek(subjek_id):
    try:
        subjek = SubjekBuku.query.get_or_404(subjek_id)
        nama_subjek = request.form.get('nama_subjek')
        
        # Check if subject name already exists (except current record)
        existing_subjek = SubjekBuku.query.filter_by(nama=nama_subjek).first()
        if existing_subjek and existing_subjek.id != subjek_id:
            return jsonify({'success': False, 'message': f'Subjek "{nama_subjek}" sudah ada.'})
        
        # Update subject
        subjek.nama = nama_subjek
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Subjek berhasil diupdate menjadi "{nama_subjek}".'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal mengupdate subjek: {str(e)}'})

@bp.route('/subjek/delete/<int:subjek_id>', methods=['DELETE'])
@superadmin_login_required
def delete_subjek(subjek_id):
    try:
        subjek = SubjekBuku.query.get_or_404(subjek_id)
        
        # Check if subject is being used in detail_kebutuhan_koleksi
        kebutuhan_count = DetailKebutuhanKoleksi.query.filter_by(subjek_id=subjek_id).count()
        if kebutuhan_count > 0:
            return jsonify({'success': False, 'message': f'Tidak dapat menghapus subjek "{subjek.nama}" karena masih digunakan dalam {kebutuhan_count} detail permintaan buku.'})
        
        # Delete the subject
        subjek_nama = subjek.nama
        db.session.delete(subjek)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Subjek "{subjek_nama}" berhasil dihapus.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menghapus subjek: {str(e)}'})

@bp.route('/donatur')
@superadmin_login_required
def daftar_donatur():
    # Query untuk menampilkan setiap donatur HANYA SEKALI dengan agregat data:
    # - jumlah_subjek: menghitung subjek UNIK yang pernah didonasikan
    # - total_books: menjumlahkan SEMUA buku dari semua donasi user
    data_donatur = db.session.query(
        User.id,
        User.full_name,
        User.username,
        User.email,
        func.count(func.distinct(DetailDonasi.subjek_id)).label('jumlah_subjek'),  # Count unique subjects
        func.sum(DetailDonasi.jumlah).label('total_books')  # Sum all books across all donations
    )\
     .join(Donasi, Donasi.user_id == User.id)\
     .join(DetailDonasi, DetailDonasi.donasi_id == Donasi.id)\
     .filter(Donasi.status == 'confirmed')\
     .group_by(User.id)\
     .order_by(User.full_name.asc())\
     .all()

    return render_template('superadmin/donatur.html', data_donatur=data_donatur)

# ==== Donasi (updated routes) ====
ALLOWED_CERT_EXT = {'png', 'jpg', 'jpeg'}
UPLOAD_SUBDIR = os.path.join('static', 'public', 'sertifikat-donasi')
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB in bytes

def allowed_ext(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_CERT_EXT

def validate_file_size(file):
    """Validate file size (max 2MB)"""
    if file and hasattr(file, 'content_length') and file.content_length:
        return file.content_length <= MAX_FILE_SIZE
    
    # Fallback: read file size
    if file:
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Reset file pointer
        return size <= MAX_FILE_SIZE
    
    return True

@bp.route('/donasi', strict_slashes=False)
@superadmin_login_required
def list_donasi():
    # Sort by status with pending first, then by ID descending
    donasi_query = Donasi.query.order_by(
        case(
            (Donasi.status == 'pending', 1),
            (Donasi.status == 'confirmed', 2),
            (Donasi.status == 'draft', 3),
            else_=4
        ),
        Donasi.id.desc()
    ).all()
    
    donasi_list = []
    for d in donasi_query:
        total_detail = db.session.query(func.count(DetailDonasi.id)).filter_by(donasi_id=d.id).scalar()
        donasi_list.append({
            'id': d.id,
            'invoice': d.invoice,
            'user': d.user,
            'status': d.status,
            'sertifikat': d.sertifikat,
            'created_at': d.created_at,
            'total_detail': total_detail,
            # tambahkan baris berikut agar data muncul di kolom Subjek Buku dan Jumlah Buku
            'subjek_buku': d.subjek_buku,
            'jumlah_buku': sum(det.jumlah for det in d.details)
        })
    
    # Calculate donation statistics for the status cards
    count_of_draft_donations = db.session.query(func.count(Donasi.id)).filter(Donasi.status == 'draft').scalar() or 0
    count_of_pending_donations = db.session.query(func.count(Donasi.id)).filter(Donasi.status == 'pending').scalar() or 0
    count_of_confirmed_donations = db.session.query(func.count(Donasi.id)).filter(Donasi.status == 'confirmed').scalar() or 0
    
    # ✅ UPDATE: Only count donations with status 'confirmed' for total books and total donations
    # Calculate total books donated across donations with status 'confirmed' only
    total_books_donated = db.session.query(func.sum(DetailDonasi.jumlah))\
        .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
        .filter(Donasi.status == 'confirmed')\
        .scalar() or 0
    
    # Calculate total count of donations with status 'confirmed' only
    total_count_of_donations = db.session.query(func.count(Donasi.id))\
        .filter(Donasi.status == 'confirmed')\
        .scalar() or 0
    
    stats_donasi = {
        'draft': count_of_draft_donations,
        'pending': count_of_pending_donations,
        'confirmed': count_of_confirmed_donations,
        'total_books': total_books_donated,
        'total': total_count_of_donations
    }
    
    return render_template('superadmin/donasi.html', donasi_list=donasi_list, stats_donasi=stats_donasi)

@bp.route('/donasi/<int:donasi_id>')
@superadmin_login_required
def get_detail(donasi_id):
    try:
        d = Donasi.query.get_or_404(donasi_id)
        details = DetailDonasi.query.filter_by(donasi_id=donasi_id).all()
        detail_items = []
        for det in details:
            detail_items.append({
                'id': det.id,
                'item': det.subjek.nama if det.subjek else 'Unknown',
                'judul_buku': det.judul_buku,
                'jumlah': det.jumlah,
                'diterima': det.diterima,
                'ditolak': det.ditolak,
                'alasan_ditolak': det.alasan_ditolak,
            })
        
        return jsonify({
            'success': True,
            'id': d.id,
            'invoice': d.invoice,
            'status': d.status,
            'whatsapp': d.whatsapp,
            'metode': d.metode,
            'sampul_buku': d.sampul_buku,
            'bukti_pengiriman': d.bukti_pengiriman,
            'sertifikat': d.sertifikat,
            'details': detail_items
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Gagal memuat detail: {str(e)}'})

@bp.route('/donasi/<int:donasi_id>/edit', methods=['POST'])
@superadmin_login_required
def edit_donasi(donasi_id):
    try:
        d = Donasi.query.get_or_404(donasi_id)
        
        # Store original values for email decision logic
        original_status = d.status
        original_certificate = d.sertifikat
        
        # Update basic fields
        old_status = d.status
        status = request.form.get('status', d.status)
        d.status = status
        
        # Update detail donasi fields
        details = DetailDonasi.query.filter_by(donasi_id=donasi_id).all()
        for detail in details:
            # Get individual field values for this detail
            diterima_key = f'detail_{detail.id}_diterima'
            ditolak_key = f'detail_{detail.id}_ditolak'
            alasan_key = f'detail_{detail.id}_alasan_ditolak'
            
            diterima = request.form.get(diterima_key)
            ditolak = request.form.get(ditolak_key)
            alasan_ditolak = request.form.get(alasan_key)
            
            # Update detail fields
            if diterima is not None:
                detail.diterima = int(diterima) if diterima else 0
                # ✅ UPDATE: Set kuota equal to diterima when status is confirmed
                if status == 'confirmed':
                    detail.kuota = detail.diterima
            if ditolak is not None:
                detail.ditolak = int(ditolak) if ditolak else 0
            if alasan_ditolak is not None:
                detail.alasan_ditolak = alasan_ditolak.strip() if alasan_ditolak else None

        # Handle certificate upload
        file = request.files.get('sertifikat')
        certificate_uploaded = False
        certificate_filename = d.sertifikat  # Keep existing certificate filename
        
        # Check if certificate is required (only if no existing certificate)
        if not d.sertifikat and (not file or not file.filename):
            return jsonify({'ok': False, 'msg': 'Sertifikat donasi wajib diupload untuk donasi yang belum memiliki sertifikat'}), 400
        
        # If new file is uploaded, process it
        if file and file.filename:
            if not allowed_ext(file.filename):
                return jsonify({'ok': False, 'msg': 'Ekstensi sertifikat tidak diizinkan (hanya PNG, JPG, JPEG)'}), 400
            if not validate_file_size(file):
                return jsonify({'ok': False, 'msg': 'Ukuran file sertifikat melebihi batas maksimal 2MB'}), 400

            # Generate a unique hash-based filename
            original = secure_filename(file.filename)
            timestamp = int(datetime.utcnow().timestamp())
            hash_src = f"{d.id}_{timestamp}_{original}".encode('utf-8')
            hash_hex = hashlib.sha256(hash_src).hexdigest()
            ext = os.path.splitext(original)[1]
            filename = f"{hash_hex}{ext}"

            upload_dir_abs = os.path.join(current_app.root_path, UPLOAD_SUBDIR)
            os.makedirs(upload_dir_abs, exist_ok=True)

            # Remove old certificate if exists
            if d.sertifikat:
                old_path = os.path.join(upload_dir_abs, d.sertifikat)
                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass

            # Save new certificate
            file.save(os.path.join(upload_dir_abs, filename))
            d.sertifikat = filename
            certificate_filename = filename
            certificate_uploaded = True
        else:
            # If no new file, keep the existing certificate filename
            certificate_filename = d.sertifikat

        # Commit changes first
        db.session.commit()
        
        # Email notification logic - only send if:
        # 1. Status changed from non-confirmed to confirmed AND certificate exists, OR
        # 2. Status is confirmed AND certificate was just uploaded (new certificate)
        should_send_email = False
        
        if (status == 'confirmed' and certificate_filename and d.user and d.user.email):
            # Case 1: Status changed from non-confirmed to confirmed
            if original_status != 'confirmed' and status == 'confirmed':
                should_send_email = True
                current_app.logger.info(f"Email trigger: Status changed from {original_status} to confirmed")
            
            # Case 2: New certificate uploaded for confirmed donation
            elif original_status == 'confirmed' and certificate_uploaded:
                should_send_email = True
                current_app.logger.info(f"Email trigger: New certificate uploaded for confirmed donation")
            
            # Case 3: Already confirmed with existing certificate - NO EMAIL
            elif original_status == 'confirmed' and original_certificate and not certificate_uploaded:
                should_send_email = False
                current_app.logger.info(f"Email skipped: Donation already confirmed with existing certificate")
        
        if should_send_email:
            try:
                email_service = EmailService()
                success, message = email_service.send_donation_confirmation(
                    donatur_email=d.user.email,
                    donatur_name=d.user.full_name or d.user.username,
                    invoice=d.invoice or f'INV-{d.id}',
                    certificate_filename=certificate_filename
                )
                
                if success:
                    current_app.logger.info(f"Email sent successfully to {d.user.email} for donation {d.id}")
                    return jsonify({'ok': True, 'msg': 'Donasi berhasil diperbarui dan notifikasi email telah dikirim'})
                else:
                    current_app.logger.warning(f"Failed to send email to {d.user.email}: {message}")
                    return jsonify({'ok': True, 'msg': f'Donasi berhasil diperbarui, tetapi gagal mengirim email: {message}'})
            
            except Exception as e:
                current_app.logger.error(f"Error sending email notification: {str(e)}")
                return jsonify({'ok': True, 'msg': f'Donasi berhasil diperbarui, tetapi gagal mengirim email: {str(e)}'})
        else:
            # No email needed
            return jsonify({'ok': True, 'msg': 'Donasi berhasil diperbarui'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in edit_donasi: {str(e)}")
        return jsonify({'ok': False, 'msg': f'Gagal memperbarui donasi: {str(e)}'})

@bp.route('/donasi/<int:donasi_id>', methods=['DELETE'])
@superadmin_login_required
def delete_donasi(donasi_id):
    try:
        d = Donasi.query.get_or_404(donasi_id)
        
        # Delete detail donasi records
        DetailDonasi.query.filter_by(donasi_id=donasi_id).delete()
        
        # Delete certificate file if exists
        if d.sertifikat:
            upload_dir_abs = os.path.join(current_app.root_path, UPLOAD_SUBDIR)
            old_path = os.path.join(upload_dir_abs, d.sertifikat)
            if os.path.isfile(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        
        # Delete sampul_buku file if exists
        if d.sampul_buku:
            sampul_dir_abs = os.path.join(current_app.root_path, 'static', 'public', 'sampul-buku')
            sampul_path = os.path.join(sampul_dir_abs, d.sampul_buku)
            if os.path.isfile(sampul_path):
                try:
                    os.remove(sampul_path)
                except OSError:
                    pass
        
        # Delete bukti_pengiriman file if exists
        if d.bukti_pengiriman:
            bukti_dir_abs = os.path.join(current_app.root_path, 'static', 'public', 'bukti-pengiriman')
            bukti_path = os.path.join(bukti_dir_abs, d.bukti_pengiriman)
            if os.path.isfile(bukti_path):
                try:
                    os.remove(bukti_path)
                except OSError:
                    pass
        
        # Delete the donation record
        db.session.delete(d)
        db.session.commit()
        
        return jsonify({'ok': True, 'msg': 'Donasi dan semua file terkait berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': f'Gagal menghapus donasi: {str(e)}'})

@bp.route('/riwayat-distribusi')
@superadmin_login_required
def riwayat_distribusi():
    data_distribusi = db.session.query(RiwayatDistribusi)\
        .options(joinedload(RiwayatDistribusi.perpus),
                joinedload(RiwayatDistribusi.detail_riwayat_distribusi).joinedload(DetailRiwayatDistribusi.subjek),
                joinedload(RiwayatDistribusi.detail_riwayat_distribusi).joinedload(DetailRiwayatDistribusi.donasi))\
        .order_by(RiwayatDistribusi.id.desc())\
        .all()
    
    # Calculate statistics for distribution status
    count_pengiriman = sum(1 for d in data_distribusi if d.status == 'pengiriman')
    count_diterima = sum(1 for d in data_distribusi if d.status == 'diterima')
    
    # Calculate total quota books from DetailDonasi
    total_kuota_buku = db.session.query(func.sum(DetailDonasi.kuota))\
        .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
        .filter(Donasi.status == 'confirmed')\
        .scalar() or 0
    
    # Calculate quota by subject
    kuota_per_subjek = db.session.query(
        SubjekBuku.nama.label('subjek_nama'),
        func.sum(DetailDonasi.kuota).label('total_kuota')
    )\
    .join(DetailDonasi, DetailDonasi.subjek_id == SubjekBuku.id)\
    .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
    .filter(Donasi.status == 'confirmed')\
    .filter(DetailDonasi.kuota > 0)\
    .group_by(SubjekBuku.id, SubjekBuku.nama)\
    .order_by(SubjekBuku.nama.asc())\
    .all()
    
    stats_distribusi = {
        'pengiriman': count_pengiriman,
        'diterima': count_diterima,
        'total_kuota': total_kuota_buku
    }
    
    return render_template('superadmin/riwayat_distribusi.html', 
                         data_distribusi=data_distribusi, 
                         stats_distribusi=stats_distribusi,
                         kuota_per_subjek=kuota_per_subjek)

@bp.route('/riwayat-distribusi/detail/<int:distribusi_id>')
@superadmin_login_required
def detail_distribusi(distribusi_id):
    distribusi = RiwayatDistribusi.query.options(
        joinedload(RiwayatDistribusi.perpus).joinedload(PerpusDesa.detail_perpus),
        joinedload(RiwayatDistribusi.detail_riwayat_distribusi).joinedload(DetailRiwayatDistribusi.subjek),
        joinedload(RiwayatDistribusi.detail_riwayat_distribusi).joinedload(DetailRiwayatDistribusi.donasi).joinedload(Donasi.user)
    ).get_or_404(distribusi_id)
    
    # Get unique donator names from all related donations
    donatur_names = []
    seen_donatur_ids = set()
    for detail in distribusi.detail_riwayat_distribusi:
        if detail.donasi and detail.donasi.user and detail.donasi.user.id not in seen_donatur_ids:
            donatur_names.append(detail.donasi.user.full_name)
            seen_donatur_ids.add(detail.donasi.user.id)
    
    # Add donatur_names to distribusi object for template access
    distribusi.donatur_names = donatur_names
    
    return render_template('superadmin/partials/detail_distribusi.html', distribusi=distribusi)

@bp.route('/riwayat-distribusi/edit/<int:distribusi_id>')
@superadmin_login_required
def edit_distribusi_form(distribusi_id):
    distribusi = RiwayatDistribusi.query.options(
        joinedload(RiwayatDistribusi.perpus),
        joinedload(RiwayatDistribusi.detail_riwayat_distribusi).joinedload(DetailRiwayatDistribusi.subjek)
    ).get_or_404(distribusi_id)
    
    return render_template('superadmin/partials/edit_distribusi.html', distribusi=distribusi)

@bp.route('/riwayat-distribusi/update/<int:distribusi_id>', methods=['POST'])
@superadmin_login_required
def update_distribusi(distribusi_id):
    try:
        distribusi = RiwayatDistribusi.query.get_or_404(distribusi_id)
        
        # Update basic fields
        distribusi.status = request.form.get('status', distribusi.status)
        
        # Handle bukti foto upload
        file = request.files.get('bukti_foto')
        if file and file.filename:
            if not allowed_ext(file.filename):
                return jsonify({'success': False, 'message': 'Ekstensi file tidak diizinkan (hanya PNG, JPG, JPEG)'})
            
            filename = secure_filename(f"distribusi_{distribusi.id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
            upload_dir_abs = os.path.join(current_app.root_path, 'static', 'public', 'bukti-distribusi')
            os.makedirs(upload_dir_abs, exist_ok=True)
            
            # Remove old file if exists
            if distribusi.bukti_foto:
                old_path = os.path.join(upload_dir_abs, distribusi.bukti_foto)
                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
            
            file.save(os.path.join(upload_dir_abs, filename))
            distribusi.bukti_foto = filename

        # Update detail distribusi
        for detail in distribusi.detail_riwayat_distribusi:
            jumlah_key = f'detail_{detail.id}_jumlah'
            jumlah = request.form.get(jumlah_key)
            if jumlah is not None:
                detail.jumlah = int(jumlah) if jumlah else 0

        db.session.commit()
        return jsonify({'success': True, 'message': 'Data distribusi berhasil diperbarui'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal memperbarui data: {str(e)}'})

@bp.route('/riwayat-distribusi/delete/<int:distribusi_id>', methods=['DELETE'])
@superadmin_login_required
def delete_distribusi(distribusi_id):
    try:
        distribusi = RiwayatDistribusi.query.get_or_404(distribusi_id)
        
        # Delete detail records
        DetailRiwayatDistribusi.query.filter_by(distribusi_id=distribusi_id).delete()
        
        # Delete bukti foto file if exists
        if distribusi.bukti_foto:
            upload_dir_abs = os.path.join(current_app.root_path, 'static', 'public', 'bukti-distribusi')
            old_path = os.path.join(upload_dir_abs, distribusi.bukti_foto)
            if os.path.isfile(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        
        db.session.delete(distribusi)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data distribusi berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menghapus data: {str(e)}'})

@bp.route('/riwayat-distribusi/tambah', methods=['GET', 'POST'])
@superadmin_login_required
def tambah_distribusi():
    if request.method == 'POST':
        try:
            perpus_id = request.form.get('perpus_id')
            status = request.form.get('status', 'pengiriman')
            distribution_data_str = request.form.get('distribution_data')
            
            # Validate required fields
            if not perpus_id or not distribution_data_str:
                return jsonify({'success': False, 'message': 'Data distribusi tidak lengkap.'})
            
            # Validate perpus exists
            perpus = PerpusDesa.query.get(perpus_id)
            if not perpus:
                return jsonify({'success': False, 'message': 'Perpustakaan tidak ditemukan.'})
            
            try:
                distribution_data = json.loads(distribution_data_str)
            except json.JSONDecodeError:
                return jsonify({'success': False, 'message': 'Format data distribusi tidak valid.'})
            
            if not distribution_data:
                return jsonify({'success': False, 'message': 'Tidak ada data distribusi yang dipilih.'})
            
            # Start transaction
            try:
                # Create new distribution record
                distribusi = RiwayatDistribusi(
                    perpus_id=perpus_id,
                    status=status
                )
                db.session.add(distribusi)
                db.session.flush()  # Get the ID without committing
                
                total_distributed = 0
                
                # Process each subjek distribution
                for subjek_data in distribution_data:
                    subjek_id = subjek_data.get('subjek_id')
                    jumlah_distribusi = subjek_data.get('jumlah_distribusi')
                    donations = subjek_data.get('donations', [])
                    
                    if not subjek_id or not jumlah_distribusi or not donations:
                        continue
                    
                    # Validate subjek exists
                    subjek = SubjekBuku.query.get(subjek_id)
                    if not subjek:
                        continue
                    
                    # Validate total available quota
                    total_available = sum(d.get('kuota', 0) for d in donations)
                    if jumlah_distribusi > total_available:
                        return jsonify({'success': False, 'message': f'Jumlah distribusi melebihi kuota yang tersedia untuk subjek {subjek.nama}.'})
                    
                    # Distribute books across selected donations
                    remaining_to_distribute = jumlah_distribusi
                    
                    for donation in donations:
                        if remaining_to_distribute <= 0:
                            break
                        
                        donasi_id = donation.get('donasi_id')
                        detail_id = donation.get('detail_id')
                        available_kuota = donation.get('kuota', 0)
                        
                        if not donasi_id or not detail_id:
                            continue
                        
                        # Validate donation exists and has quota
                        detail_donasi = DetailDonasi.query.get(detail_id)
                        if not detail_donasi or detail_donasi.kuota <= 0:
                            continue
                        
                        # Calculate how much to take from this donation (use actual current kuota)
                        actual_available = min(available_kuota, detail_donasi.kuota)
                        amount_to_take = min(remaining_to_distribute, actual_available)
                        
                        if amount_to_take > 0:
                            # Create detail distribution record
                            detail_distribusi = DetailRiwayatDistribusi(
                                distribusi_id=distribusi.id,
                                donasi_id=donasi_id,
                                subjek_id=subjek_id,
                                jumlah=amount_to_take
                            )
                            db.session.add(detail_distribusi)
                            
                            # Update kuota in detail_donasi
                            detail_donasi.kuota = max(0, detail_donasi.kuota - amount_to_take)
                            
                            remaining_to_distribute -= amount_to_take
                            total_distributed += amount_to_take
                
                if total_distributed == 0:
                    return jsonify({'success': False, 'message': 'Tidak ada buku yang berhasil didistribusikan.'})
                
                # Handle bukti foto upload
                file = request.files.get('bukti_foto')
                if file and file.filename:
                    if not allowed_ext(file.filename):
                        return jsonify({'success': False, 'message': 'Ekstensi file tidak diizinkan (hanya PNG, JPG, JPEG)'})
                    
                    filename = secure_filename(f"distribusi_{distribusi.id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                    upload_dir_abs = os.path.join(current_app.root_path, 'static', 'public', 'bukti-distribusi')
                    os.makedirs(upload_dir_abs, exist_ok=True)
                    
                    file.save(os.path.join(upload_dir_abs, filename))
                    distribusi.bukti_foto = filename
                
                # Commit all changes
                db.session.commit()
                return jsonify({'success': True, 'message': f'Riwayat distribusi berhasil ditambahkan. Total {total_distributed} buku didistribusikan.'})
                
            except Exception as e:
                db.session.rollback()
                raise e
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error in tambah_distribusi: {str(e)}')
            return jsonify({'success': False, 'message': f'Gagal menyimpan data: {str(e)}'})
    
    # GET request - return form data
    perpus_list = PerpusDesa.query.order_by(PerpusDesa.nama.asc()).all()
    subjek_list = SubjekBuku.query.order_by(SubjekBuku.nama.asc()).all()
    
    return render_template('superadmin/partials/tambah_distribusi.html', 
                         perpus_list=perpus_list, subjek_list=subjek_list)
    
@bp.route('/pengajuan-perpusdes')
@superadmin_login_required
def pengajuan_perpusdes():
    # Get kebutuhan koleksi data with perpus and total books calculation
    # Custom ordering: Status Pending first, then Priority Tinggi first, then by date
    from sqlalchemy import case
    
    data_pengajuan = db.session.query(KebutuhanKoleksi)\
        .options(joinedload(KebutuhanKoleksi.perpus),
                joinedload(KebutuhanKoleksi.detail_kebutuhan).joinedload(DetailKebutuhanKoleksi.subjek))\
        .order_by(
            case(
                (KebutuhanKoleksi.status == 'pending', 1),
                (KebutuhanKoleksi.status == 'approved', 2),
                (KebutuhanKoleksi.status == 'rejected', 3),
                else_=4
            ),
            case(
                (KebutuhanKoleksi.prioritas == 'tinggi', 1),
                (KebutuhanKoleksi.prioritas == 'sedang', 2),
                (KebutuhanKoleksi.prioritas == 'rendah', 3),
                else_=4
            ),
            KebutuhanKoleksi.tanggal_pengajuan.desc()
        )\
        .all()
    
    # Calculate total books for each kebutuhan
    for kebutuhan in data_pengajuan:
        kebutuhan.total_buku = sum(detail.jumlah_buku for detail in kebutuhan.detail_kebutuhan)
    
    # Statistics for pengajuan
    count_of_pending_requests = sum(1 for k in data_pengajuan if k.status == 'pending')
    count_of_approved_requests = sum(1 for k in data_pengajuan if k.status == 'approved')
    count_of_rejected_requests = sum(1 for k in data_pengajuan if k.status == 'rejected')
    total_count_of_requests = len(data_pengajuan)
    
    stats_pengajuan = {
        'pending': count_of_pending_requests,
        'approved': count_of_approved_requests, 
        'rejected': count_of_rejected_requests,
        'total': total_count_of_requests
    }
    
    return render_template('superadmin/pengajuan_perpusdes.html', data_pengajuan=data_pengajuan, stats_pengajuan=stats_pengajuan)

@bp.route('/pengajuan-perpusdes/detail/<int:pengajuan_id>')
@superadmin_login_required
def detail_pengajuan_perpusdes(pengajuan_id):
    pengajuan = KebutuhanKoleksi.query.options(
        joinedload(KebutuhanKoleksi.perpus),
        joinedload(KebutuhanKoleksi.detail_kebutuhan).joinedload(DetailKebutuhanKoleksi.subjek)
    ).get_or_404(pengajuan_id)
    
    return render_template('superadmin/partials/detail_pengajuan.html', pengajuan=pengajuan)

@bp.route('/pengajuan-perpusdes/update-status/<int:pengajuan_id>', methods=['POST'])
@superadmin_login_required
def update_status_pengajuan(pengajuan_id):
    try:
        pengajuan = KebutuhanKoleksi.query.get_or_404(pengajuan_id)
        
        # Update status
        new_status = request.form.get('status')
        if new_status not in ['pending', 'approved', 'rejected']:
            return jsonify({'success': False, 'message': 'Status tidak valid.'})
        
        pengajuan.status = new_status
        
        # Update pesan if provided
        pesan = request.form.get('pesan', '').strip()
        if pesan:
            pengajuan.pesan = pesan
        else:
            pengajuan.pesan = None
        
        db.session.commit()
        
        status_text = {
            'pending': 'Menunggu',
            'approved': 'Disetujui', 
            'rejected': 'Ditolak'
        }
        
        return jsonify({'success': True, 'message': f'Status pengajuan berhasil diubah menjadi "{status_text[new_status]}".'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal mengubah status: {str(e)}'})

@bp.route('/pengajuan-perpusdes/delete/<int:pengajuan_id>', methods=['DELETE'])
@superadmin_login_required
def delete_pengajuan_perpusdes(pengajuan_id):
    try:
        # Get the pengajuan with related data
        pengajuan = KebutuhanKoleksi.query.options(
            joinedload(KebutuhanKoleksi.perpus),
            joinedload(KebutuhanKoleksi.detail_kebutuhan)
        ).get_or_404(pengajuan_id)
        
        perpus_nama = pengajuan.perpus.nama if pengajuan.perpus else 'Unknown'
        
        # Delete related detail_kebutuhan_koleksi records first (foreign key constraint)
        detail_count = len(pengajuan.detail_kebutuhan)
        DetailKebutuhanKoleksi.query.filter_by(kebutuhan_id=pengajuan_id).delete()
        
        # Delete the main kebutuhan_koleksi record
        db.session.delete(pengajuan)
        
        # Commit the transaction
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Pengajuan dari "{perpus_nama}" berhasil dihapus. {detail_count} detail subjek buku juga telah dihapus.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting pengajuan {pengajuan_id}: {str(e)}')
        return jsonify({
            'success': False, 
            'message': f'Gagal menghapus pengajuan: {str(e)}'
        })

# API Endpoints for Distribution Form
@bp.route('/api/subjects')
@superadmin_login_required
def api_get_subjects():
    """Get all available subjects"""
    try:
        subjects = SubjekBuku.query.order_by(SubjekBuku.nama.asc()).all()
        subjects_data = [{'id': s.id, 'nama': s.nama} for s in subjects]
        return jsonify(subjects_data)
    except Exception as e:
        return jsonify({'error': f'Gagal memuat subjects: {str(e)}'})

@bp.route('/api/available-donations')
@superadmin_login_required
def api_get_available_donations():
    """Get donations with available quota for distribution"""
    try:
        # Get donations with confirmed status and available quota
        donations_query = db.session.query(Donasi)\
            .join(DetailDonasi, DetailDonasi.donasi_id == Donasi.id)\
            .filter(Donasi.status == 'confirmed')\
            .filter(DetailDonasi.kuota > 0)\
            .options(joinedload(Donasi.user), joinedload(Donasi.details).joinedload(DetailDonasi.subjek))\
            .distinct()\
            .order_by(Donasi.created_at.desc())\
            .all()
        
        donations_data = []
        for donasi in donations_query:
            # Only include details with kuota > 0
            available_details = [
                {
                    'id': detail.id,
                    'subjek_id': detail.subjek_id,
                    'subjek_nama': detail.subjek.nama if detail.subjek else '',
                    'kuota': detail.kuota,
                    'jumlah_original': detail.jumlah
                }
                for detail in donasi.details if detail.kuota > 0
            ]
            
            if available_details:  # Only include donation if it has available details
                donations_data.append({
                    'id': donasi.id,
                    'invoice': donasi.invoice,
                    'donatur': donasi.user.full_name if donasi.user else 'Unknown',
                    'created_at': donasi.created_at.strftime('%d/%m/%Y') if donasi.created_at else '',
                    'details': available_details
                })
        
        return jsonify(donations_data)
    except Exception as e:
        return jsonify({'error': f'Gagal memuat donations: {str(e)}'})

@bp.route('/api/donation-details/<int:donasi_id>')
@superadmin_login_required  
def api_get_donation_details(donasi_id):
    """Get details of a specific donation"""
    try:
        donasi = Donasi.query.options(
            joinedload(Donasi.user),
            joinedload(Donasi.details).joinedload(DetailDonasi.subjek)
        ).get_or_404(donasi_id)
        
        details_data = [
            {
                'id': detail.id,
                'subjek_id': detail.subjek_id,
                'subjek_nama': detail.subjek.nama if detail.subjek else '',
                'jumlah': detail.jumlah,
                'diterima': detail.diterima,
                'kuota': detail.kuota
            }
            for detail in donasi.details
        ]
        
        donation_data = {
            'id': donasi.id,
            'invoice': donasi.invoice,
            'donatur': donasi.user.full_name if donasi.user else 'Unknown',
            'status': donasi.status,
            'created_at': donasi.created_at.strftime('%d/%m/%Y') if donasi.created_at else '',
            'details': details_data
        }
        
        return jsonify(donation_data)
    except Exception as e:
        return jsonify({'error': f'Gagal memuat detail donasi: {str(e)}'})

@bp.route('/statistik')
@superadmin_login_required
def statistik():
    # Get current year and available years
    current_year = datetime.now().year
    available_years_query = db.session.query(
        func.extract('year', Donasi.created_at).label('year')
    ).distinct().filter(
        func.extract('year', Donasi.created_at).isnot(None)
    ).order_by('year').all()
    
    available_years = [int(year.year) for year in available_years_query if year.year]
    if current_year not in available_years:
        available_years.append(current_year)
    available_years.sort(reverse=True)
    
    # Get perpus list and kecamatan list - Convert to serializable format
    perpus_query = PerpusDesa.query.order_by(PerpusDesa.nama.asc()).all()
    perpus_list = [
        {
            'id': perpus.id,
            'nama': perpus.nama,
            'kecamatan': perpus.kecamatan,
            'desa': perpus.desa
        }
        for perpus in perpus_query
    ]
    
    kecamatan_list = db.session.query(PerpusDesa.kecamatan).distinct().order_by(PerpusDesa.kecamatan.asc()).all()
    kecamatan_list = [k[0] for k in kecamatan_list]
    
    # Calculate statistics
    # Total buku diterima (confirmed donations only)
    total_buku_diterima = db.session.query(func.sum(DetailDonasi.diterima))\
        .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
        .filter(Donasi.status == 'confirmed')\
        .scalar() or 0
    
    # Total buku tersalurkan (from distribution records)
    total_buku_tersalurkan = db.session.query(func.sum(DetailRiwayatDistribusi.jumlah))\
        .scalar() or 0
    
    # Total kunjungan
    total_kunjungan = Kunjungan.query.count()
    
    # Top 5 subjects by total donations - Convert to serializable format
    top_subjects_query = db.session.query(
        SubjekBuku.nama,
        func.sum(DetailDonasi.diterima).label('total_donasi')
    )\
    .join(DetailDonasi, DetailDonasi.subjek_id == SubjekBuku.id)\
    .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
    .filter(Donasi.status == 'confirmed')\
    .group_by(SubjekBuku.id, SubjekBuku.nama)\
    .order_by(func.sum(DetailDonasi.diterima).desc())\
    .limit(5).all()
    
    top_subjects = [
        {
            'nama': subject.nama,
            'total_donasi': subject.total_donasi or 0
        }
        for subject in top_subjects_query
    ]
    
    # Top 5 libraries by total books received - Convert to serializable format
    top_libraries_query = db.session.query(
        PerpusDesa.nama,
        PerpusDesa.kecamatan,
        func.sum(DetailRiwayatDistribusi.jumlah).label('total_diterima')
    )\
    .join(RiwayatDistribusi, RiwayatDistribusi.perpus_id == PerpusDesa.id)\
    .join(DetailRiwayatDistribusi, DetailRiwayatDistribusi.distribusi_id == RiwayatDistribusi.id)\
    .group_by(PerpusDesa.id, PerpusDesa.nama, PerpusDesa.kecamatan)\
    .order_by(func.sum(DetailRiwayatDistribusi.jumlah).desc())\
    .limit(5).all()
    
    top_libraries = [
        {
            'nama': library.nama,
            'kecamatan': library.kecamatan,
            'total_diterima': library.total_diterima or 0
        }
        for library in top_libraries_query
    ]
    
    stats = {
        'total_buku_diterima': total_buku_diterima,
        'total_buku_tersalurkan': total_buku_tersalurkan,
        'total_kunjungan': total_kunjungan
    }
    
    return render_template('superadmin/statistik.html',
                         stats=stats,
                         perpus_list=perpus_list,
                         kecamatan_list=kecamatan_list,
                         available_years=available_years,
                         current_year=current_year,
                         top_subjects=top_subjects,
                         top_libraries=top_libraries)

# API Endpoints for Statistics Charts
@bp.route('/api/visit-data')
@superadmin_login_required
def api_visit_data():
    """Get visit data for charts with optional filters"""
    try:
        perpus_id = request.args.get('perpus_id')
        kecamatan = request.args.get('kecamatan')
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Build query with filters
        query = db.session.query(
            func.extract('month', Kunjungan.tanggal).label('month'),
            func.count(Kunjungan.id).label('count')
        )
        
        # Apply filters
        if perpus_id:
            query = query.filter(Kunjungan.perpus_id == perpus_id)
        elif kecamatan:
            query = query.join(PerpusDesa, PerpusDesa.id == Kunjungan.perpus_id)\
                         .filter(PerpusDesa.kecamatan == kecamatan)
        
        query = query.filter(func.extract('year', Kunjungan.tanggal) == year)\
                     .group_by(func.extract('month', Kunjungan.tanggal))\
                     .order_by('month')
        
        results = query.all()
        
        # Create monthly data array (12 months)
        monthly_data = [0] * 12
        total_visits = 0
        
        for result in results:
            month_index = int(result.month) - 1  # Convert to 0-based index
            if 0 <= month_index < 12:
                monthly_data[month_index] = result.count
                total_visits += result.count
        
        # Format data for Chart.js
        chart_data = [
            {'month': i + 1, 'count': count}
            for i, count in enumerate(monthly_data)
        ]
        
        return jsonify({
            'data': chart_data,
            'total': total_visits
        })
        
    except Exception as e:
        return jsonify({'error': f'Gagal memuat data kunjungan: {str(e)}'})

@bp.route('/api/donation-data/<int:year>')
@superadmin_login_required
def api_donation_data(year):
    """Get donation data by subject for specified year"""
    try:
        month = request.args.get('month', type=int)
        
        query = db.session.query(
            SubjekBuku.nama.label('subjek_nama'),
            func.sum(DetailDonasi.diterima).label('total_jumlah')
        )\
        .join(DetailDonasi, DetailDonasi.subjek_id == SubjekBuku.id)\
        .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
        .filter(Donasi.status == 'confirmed')\
        .filter(func.extract('year', Donasi.created_at) == year)
        
        if month:
            query = query.filter(func.extract('month', Donasi.created_at) == month)
        
        results = query.group_by(SubjekBuku.id, SubjekBuku.nama)\
        .order_by(func.sum(DetailDonasi.diterima).desc())\
        .all()
        
        chart_data = [
            {
                'subjek_nama': result.subjek_nama,
                'total_jumlah': result.total_jumlah or 0
            }
            for result in results
        ]
        
        return jsonify({
            'data': chart_data,
            'total': sum(item['total_jumlah'] for item in chart_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Gagal memuat data donasi: {str(e)}'})

@bp.route('/api/distribution-data/<int:year>')
@superadmin_login_required
def api_distribution_data(year):
    """Get distribution data by month for specified year"""
    try:
        results = db.session.query(
            func.extract('month', RiwayatDistribusi.created_at).label('month'),
            func.sum(DetailRiwayatDistribusi.jumlah).label('count')
        )\
        .join(DetailRiwayatDistribusi, DetailRiwayatDistribusi.distribusi_id == RiwayatDistribusi.id)\
        .filter(func.extract('year', RiwayatDistribusi.created_at) == year)\
        .group_by(func.extract('month', RiwayatDistribusi.created_at))\
        .order_by('month')\
        .all()
        
        # Create monthly data array (12 months)
        monthly_data = [0] * 12
        total_distributed = 0
        
        for result in results:
            month_index = int(result.month) - 1  # Convert to 0-based index
            if 0 <= month_index < 12:
                monthly_data[month_index] = result.count or 0
                total_distributed += result.count or 0
        
        # Format data for Chart.js
        chart_data = [
            {'month': i + 1, 'count': count}
            for i, count in enumerate(monthly_data)
        ]
        
        return jsonify({
            'data': chart_data,
            'total': total_distributed
        })
        
    except Exception as e:
        return jsonify({'error': f'Gagal memuat data distribusi: {str(e)}'})

@bp.route('/test-email', methods=['GET', 'POST'])
@superadmin_login_required
def test_email():
    if request.method == 'POST':
        test_email_address = request.form.get('email')
        if not test_email_address:
            return jsonify({'success': False, 'message': 'Email address is required'})
        
        try:
            email_service = EmailService()
            success, message = email_service.send_test_email(test_email_address)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'message': message})
                
        except Exception as e:
            current_app.logger.error(f"Test email error: {str(e)}")
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    # GET request - show test email form with current configuration
    email_config = {
        'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
        'MAIL_PORT': current_app.config.get('MAIL_PORT'),
        'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': current_app.config.get('MAIL_PASSWORD'),
        'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
        'MAIL_USE_SSL': current_app.config.get('MAIL_USE_SSL'),
        'MAIL_DEFAULT_SENDER': current_app.config.get('MAIL_DEFAULT_SENDER')
    }
    
    return render_template('superadmin/test_email.html', config=email_config)
