import os
import re
import platform
from datetime import datetime
import hashlib
import pdfkit
from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
    send_file, current_app, send_from_directory, jsonify
)
from werkzeug.utils import secure_filename
from app.models import db, User, Donasi, DetailDonasi, KegiatanPerpus, PerpusDesa, DetailPerpus, SubjekBuku, RiwayatDistribusi, DetailRiwayatDistribusi
from app.utils.session_manager import SessionManager
from authlib.integrations.flask_client import OAuth
from sqlalchemy import or_, func, distinct
import random

# Buat Blueprint untuk rute publik
bp = Blueprint('public', __name__)

# Add this new function to make SessionManager available in templates
@bp.context_processor
def inject_session_manager():
    return {'SessionManager': SessionManager}

# Fungsi bantuan untuk memeriksa ekstensi file yang diizinkan
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_slug(text):
    """Convert text to URL-friendly slug"""
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug

def create_perpus_slug(perpus_name, kecamatan_name=None):
    """Convert perpus name and kecamatan to URL-friendly slug for perpus"""
    if not perpus_name:
        return 'perpusdesa'
    
    # Clean perpus name
    clean_perpus = perpus_name.lower()
    clean_perpus = clean_perpus.replace('perpustakaan', '').replace('perpusdes', '').replace('desa', '').replace('tbm', '')
    clean_perpus = re.sub(r'[^a-zA-Z0-9\s-]', '', clean_perpus).strip()
    clean_perpus = re.sub(r'[-\s]+', '', clean_perpus)
    
    # Clean kecamatan name if provided
    clean_kecamatan = ''
    if kecamatan_name:
        clean_kecamatan = kecamatan_name.lower()
        clean_kecamatan = clean_kecamatan.replace('kecamatan', '').replace('kec', '')
        clean_kecamatan = re.sub(r'[^a-zA-Z0-9\s-]', '', clean_kecamatan).strip()
        clean_kecamatan = re.sub(r'[-\s]+', '', clean_kecamatan)
    
    # Combine perpus and kecamatan
    if clean_perpus and clean_kecamatan:
        result = f'perpus{clean_perpus}{clean_kecamatan}'
    elif clean_perpus:
        result = f'perpus{clean_perpus}'
    else:
        result = 'perpusdesa'
    
    # Add debug logging
    current_app.logger.debug(f"Python slug creation: '{perpus_name}' + '{kecamatan_name}' -> '{result}'")
    return result

def format_indonesian_date(date_obj):
    """Format date to Indonesian format"""
    months = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
    
    day = date_obj.day
    month = months[date_obj.month]
    year = date_obj.year
    
    return f"{day:02d} {month} {year}"

def format_author_name(full_name):
    """Format author name from 'Admin ...' to 'Perpus ...'"""
    if not full_name:
        return 'Perpus Desa'
    
    # If full_name starts with "Admin", replace with "Perpus"
    if full_name.startswith('Admin '):
        # Extract the part after "Admin "
        perpus_part = full_name.replace('Admin ', '', 1)
        return f'Perpus {perpus_part}'
    
    # Fallback: use the full_name as is, but prefix with Perpus if it doesn't already have it
    if not full_name.lower().startswith('perpus'):
        return f'Perpus {full_name}'
    
    return full_name

@bp.route('/')
def home():
    # Get latest 3 news from kegiatan_perpus
    latest_news = db.session.query(
        KegiatanPerpus.id,
        KegiatanPerpus.nama_kegiatan,
        KegiatanPerpus.tanggal_kegiatan,
        KegiatanPerpus.deskripsi_kegiatan,
        KegiatanPerpus.foto_kegiatan,
        User.full_name.label('author_name'),
        PerpusDesa.nama.label('perpus_name'),
        PerpusDesa.kecamatan.label('kecamatan_name')
    ).join(
        User, KegiatanPerpus.user_id == User.id
    ).join(
        PerpusDesa, KegiatanPerpus.perpus_id == PerpusDesa.id
    ).filter(
        KegiatanPerpus.status == 'active'
    ).order_by(
        KegiatanPerpus.tanggal_kegiatan.desc()
    ).limit(3).all()
    
    # Format news data
    news_data = []
    for news in latest_news:
        # Create excerpt from description (strip HTML and limit to 150 chars)
        excerpt = re.sub(r'<[^>]+>', '', news.deskripsi_kegiatan)
        if len(excerpt) > 150:
            excerpt = excerpt[:150] + '...'
        
        news_data.append({
            'id': news.id,
            'title': news.nama_kegiatan,
            'author': format_author_name(news.author_name),
            'date': format_indonesian_date(news.tanggal_kegiatan),
            'image': f'public/kegiatan-perpus/{news.foto_kegiatan}' if news.foto_kegiatan else 'images/library.jpg',
            'excerpt': excerpt,
            'slug': create_slug(news.nama_kegiatan),
            'perpus_slug': create_perpus_slug(news.perpus_name, news.kecamatan_name)
        })
    
    return render_template('pengguna/index.html', latest_news=news_data)

@bp.route('/syarat')
def syarat():
    return render_template('pengguna/syarat_ketentuan.html')

@bp.route('/transparansi')
def transparansi():
    # Check if user is logged in
    if not SessionManager.is_logged_in('user'):
        flash("Silakan login terlebih dahulu untuk mengakses halaman transparansi donasi.", "warning")
        return redirect(url_for('public.login'))
    
    user_id = SessionManager.get_current_user_id('user')

    # === STATISTIK SESUAI REQUIREMENT ===
    # Subquery donasi user (semua status) dan subquery donasi user dengan status pending / confirmed
    from sqlalchemy import select, distinct
    
    subq_all_user_donasi = db.session.query(Donasi.id).filter(Donasi.user_id == user_id).subquery()
    subq_user_donasi_pending_confirmed = db.session.query(Donasi.id).filter(
        Donasi.user_id == user_id,
        Donasi.status.in_(["pending", "confirmed"])
    ).subquery()

    # Total Buku = SUM(DetailDonasi.jumlah) dari donasi user status pending/confirmed
    total_buku = db.session.query(
        func.coalesce(func.sum(DetailDonasi.jumlah), 0)
    ).filter(
        DetailDonasi.donasi_id.in_(select(subq_user_donasi_pending_confirmed))
    ).scalar()

    # Perpus Terbantu = jumlah unik perpus_id pada RiwayatDistribusi yang punya detail
    # dengan donasi_id milik user (status donasi bebas – requirement tidak membatasi status)
    perpus_terbantu = db.session.query(
        func.coalesce(func.count(distinct(RiwayatDistribusi.perpus_id)), 0)
    ).join(
        DetailRiwayatDistribusi, DetailRiwayatDistribusi.distribusi_id == RiwayatDistribusi.id
    ).filter(
        DetailRiwayatDistribusi.donasi_id.in_(select(subq_all_user_donasi))
    ).scalar()

    # Buku Didistribusikan = SUM(DetailRiwayatDistribusi.jumlah) untuk donasi user
    buku_didistribusikan = db.session.query(
        func.coalesce(func.sum(DetailRiwayatDistribusi.jumlah), 0)
    ).filter(
        DetailRiwayatDistribusi.donasi_id.in_(select(subq_all_user_donasi))
    ).scalar()

    # === DATA TABEL DISTRIBUSI (tetap, gunakan donasi user apa adanya) ===
    distribusi_query = db.session.query(
        PerpusDesa.id.label('perpus_id'),
        PerpusDesa.nama.label('perpus_nama'),
        PerpusDesa.desa.label('desa_nama'),
        PerpusDesa.kecamatan.label('kecamatan_nama'),
        RiwayatDistribusi.status,
        func.sum(DetailRiwayatDistribusi.jumlah).label('total_buku'),
        func.group_concat(SubjekBuku.nama).label('subjek_list')
    ).select_from(DetailRiwayatDistribusi)\
     .join(Donasi, DetailRiwayatDistribusi.donasi_id == Donasi.id)\
     .join(RiwayatDistribusi, DetailRiwayatDistribusi.distribusi_id == RiwayatDistribusi.id)\
     .join(PerpusDesa, RiwayatDistribusi.perpus_id == PerpusDesa.id)\
     .join(SubjekBuku, DetailRiwayatDistribusi.subjek_id == SubjekBuku.id)\
     .filter(DetailRiwayatDistribusi.donasi_id.in_(select(subq_all_user_donasi)))\
     .group_by(
        PerpusDesa.id,
        PerpusDesa.nama,
        PerpusDesa.desa,
        PerpusDesa.kecamatan,
        RiwayatDistribusi.status
    ).all()

    # Get user's donation status for better messaging
    user_donations = db.session.query(Donasi).filter(
        Donasi.user_id == user_id,
        Donasi.status.in_(['pending', 'confirmed'])
    ).all()
    
    # Check if user has any pending donations that haven't been distributed yet
    pending_donations = [d for d in user_donations if d.status == 'pending']
    confirmed_donations = [d for d in user_donations if d.status == 'confirmed']
    
    # Format distribusi_list
    distribusi_list = []
    for row in distribusi_query:
        # Process the subject list and remove duplicates
        subjek_list = row.subjek_list if row.subjek_list else '-'
        if subjek_list != '-' and ',' in subjek_list:
            # Remove duplicates and add proper spacing
            unique_subjects = list(set(subjek_list.split(',')))
            subjek_list = ', '.join(sorted(unique_subjects))
        
        distribusi_list.append({
            'perpus_nama': row.perpus_nama,
            'lokasi': f"{row.desa_nama}, {row.kecamatan_nama}",
            'total_buku': row.total_buku,
            'subjek_list': subjek_list,
            'status': 'Diterima' if row.status == 'diterima' else 'Dalam Pengiriman'
        })
    
    # Create user status message
    user_status = {
        'has_donations': len(user_donations) > 0,
        'has_pending': len(pending_donations) > 0,
        'has_confirmed': len(confirmed_donations) > 0,
        'has_distributions': len(distribusi_list) > 0,
        'total_donations': len(user_donations),
        'pending_count': len(pending_donations),
        'confirmed_count': len(confirmed_donations)
    }
    
    return render_template(
        'pengguna/transparansi_donasi.html',
        total_buku=total_buku,
        perpus_terbantu=perpus_terbantu,
        buku_didistribusikan=buku_didistribusikan,
        distribusi_list=distribusi_list,
        user_status=user_status
    )

@bp.route('/riwayat')
def riwayat():
    # Check if user is logged in
    if not SessionManager.is_logged_in('user'):
        flash("Silakan login terlebih dahulu untuk mengakses halaman riwayat transparansi.", "warning")
        return redirect(url_for('public.login'))
    
    user_id = SessionManager.get_current_user_id('user')
    
    # Get donations with their distribution data
    donasi_query = db.session.query(
        Donasi.id,
        Donasi.invoice,
        Donasi.notes,
        User.full_name.label('donatur_name'),
        func.sum(DetailDonasi.jumlah).label('total_buku'),
        func.sum(DetailDonasi.diterima).label('total_diterima'),
        func.sum(DetailDonasi.ditolak).label('tidak_sesuai'),
        func.group_concat(distinct(SubjekBuku.nama)).label('subjek_list'),
        func.count(distinct(DetailRiwayatDistribusi.distribusi_id)).label('total_distribusi')
    ).select_from(Donasi)\
     .join(User, Donasi.user_id == User.id)\
     .join(DetailDonasi, DetailDonasi.donasi_id == Donasi.id)\
     .join(SubjekBuku, DetailDonasi.subjek_id == SubjekBuku.id)\
     .outerjoin(DetailRiwayatDistribusi, DetailRiwayatDistribusi.donasi_id == Donasi.id)\
     .filter(
         Donasi.user_id == user_id,
         Donasi.status.in_(['confirmed'])
     )\
     .group_by(Donasi.id, Donasi.invoice, Donasi.notes, User.full_name)\
     .order_by(Donasi.created_at.desc())\
     .all()

    # Format donation data for template
    donasi_list = []
    for row in donasi_query:
        # Get distribution details for this donation with kecamatan
        distribusi_details = db.session.query(
            PerpusDesa.nama.label('perpus_nama'),
            PerpusDesa.kecamatan.label('kecamatan'),
            func.sum(DetailRiwayatDistribusi.jumlah).label('jumlah_buku')
        ).select_from(DetailRiwayatDistribusi)\
         .join(RiwayatDistribusi, DetailRiwayatDistribusi.distribusi_id == RiwayatDistribusi.id)\
         .join(PerpusDesa, RiwayatDistribusi.perpus_id == PerpusDesa.id)\
         .filter(DetailRiwayatDistribusi.donasi_id == row.id)\
         .group_by(PerpusDesa.id, PerpusDesa.nama, PerpusDesa.kecamatan)\
         .all()

        # Get rejection details for this donation
        rejections = db.session.query(
            SubjekBuku.nama.label('subjek_nama'),
            DetailDonasi.ditolak,
            DetailDonasi.alasan_ditolak
        ).select_from(DetailDonasi)\
         .join(SubjekBuku, DetailDonasi.subjek_id == SubjekBuku.id)\
         .filter(
             DetailDonasi.donasi_id == row.id,
             DetailDonasi.ditolak > 0,
             DetailDonasi.alasan_ditolak.isnot(None)
         ).all()

        # Process subject list
        subjek_list = row.subjek_list if row.subjek_list else ''
        if subjek_list and ',' in subjek_list:
            unique_subjects = list(set(subjek_list.split(',')))
            subjek_list = ', '.join(sorted(unique_subjects))

        # Process rejection details
        rejection_details = []
        for rejection in rejections:
            rejection_details.append({
                'subjek_nama': rejection.subjek_nama,
                'jumlah_ditolak': rejection.ditolak,
                'alasan': rejection.alasan_ditolak
            })

        donasi_list.append({
            'id': row.id,
            'invoice': row.invoice,
            'donatur_name': row.donatur_name,
            'notes': row.notes,
            'subjek_list': subjek_list if subjek_list else 'Pendidikan',
            'jumlah_buku': int(row.total_buku) if row.total_buku else 0,
            'total_diterima' : int(row.total_diterima) if row.total_diterima else 0,
            'tidak_sesuai': int(row.tidak_sesuai) if row.tidak_sesuai else 0,
            'tersalurkan': sum(int(d.jumlah_buku) for d in distribusi_details),
            'rejection_details': rejection_details,
            'distribusi_list': [
                {
                    'perpus_nama': d.perpus_nama,
                    'kecamatan': d.kecamatan,
                    'jumlah_buku': int(d.jumlah_buku)
                }
                for d in distribusi_details
            ]
        })

    return render_template('pengguna/riwayat_transparansi.html', donasi=donasi_list)

@bp.route('/faq')
def faq():
    return render_template('pengguna/faq.html')

@bp.route('/kontak')
def kontak():
    return render_template('pengguna/kontak.html')

@bp.route('/profil')
def profil():
    return render_template('pengguna/profil.html')

@bp.route('/panduan-donasi')
def panduan_donasi():
    return render_template('pengguna/panduan_donasi.html')

@bp.route('/perpusdes')
def perpusdes():
    # Query all perpusdes data with join to get details
    perpusdess_query = db.session.query(
        PerpusDesa.id,
        PerpusDesa.nama,
        PerpusDesa.kecamatan,
        PerpusDesa.desa.label('desa_nama'),
        func.coalesce(DetailPerpus.jumlah_koleksi, 0).label('jumlah_koleksi'),
        func.coalesce(DetailPerpus.jumlah_eksemplar, 0).label('jumlah_eks')
    ).outerjoin(DetailPerpus, PerpusDesa.id == DetailPerpus.perpus_id) \
     .order_by(PerpusDesa.nama) \
     .all()

    # convert Row objects ke list of dict untuk JSON serializable
    perpusdess = [dict(r._asdict()) for r in perpusdess_query]

    return render_template('pengguna/perpusdes.html', 
                          perpusdess=perpusdess)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'perpus_id': user.perpus_id,
                'is_verified': user.is_verified
            }
            # Clear any existing sessions first to avoid conflicts
            SessionManager.clear_all_sessions()
            # Set the user session with the correct role
            SessionManager.set_user_session(user_data, user.role if user.role else 'user')
            flash("Login berhasil!", "success")
            return redirect(url_for('public.home'))
        flash("Email atau password salah.", "error")
    return render_template('pengguna/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        username = email.split('@')[0] + "_user"

        if User.query.filter_by(email=email).first():
            flash("Email sudah terdaftar.", "error")
            return redirect(url_for('public.register'))

        new_user = User(
            full_name=full_name,
            email=email,
            username=username,
            role='user'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registrasi berhasil! Silakan login.", "success")
        return redirect(url_for('public.login'))
    return render_template('pengguna/register.html')

@bp.route('/logout')
def logout():
    # Clear all sessions to handle any role
    SessionManager.clear_all_sessions()
    flash("Anda telah berhasil logout.", "success")
    return redirect(url_for('public.home'))

@bp.route('/update-profile', methods=['POST'])
def update_profile():
    """Update user profile"""
    if not SessionManager.is_logged_in('user'):
        flash("Silakan login terlebih dahulu.", "warning")
        return redirect(url_for('public.login'))
    
    user_id = SessionManager.get_current_user_id('user')
    user = User.query.get(user_id)
    
    if not user:
        flash("User tidak ditemukan.", "error")
        return redirect(url_for('public.home'))
    
    try:
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Only update fields that are provided (not empty)
        changes_made = False
        
        # Validate and update username if provided
        if username and username != user.username:
            existing_username = User.query.filter(User.username == username, User.id != user_id).first()
            if existing_username:
                flash("Username sudah digunakan oleh pengguna lain.", "error")
                return redirect(url_for('public.home'))
            user.username = username
            changes_made = True
        
        # Validate and update full_name if provided
        if full_name and full_name != user.full_name:
            user.full_name = full_name
            changes_made = True
        
        # Validate and update email if provided
        if email and email != user.email:
            existing_user = User.query.filter(User.email == email, User.id != user_id).first()
            if existing_user:
                flash("Email sudah digunakan oleh pengguna lain.", "error")
                return redirect(url_for('public.home'))
            user.email = email
            changes_made = True
        
        # Password validation and update if provided
        if password:
            if len(password) < 6:
                flash("Password minimal 6 karakter.", "error")
                return redirect(url_for('public.home'))
            
            if password != confirm_password:
                flash("Password dan konfirmasi password tidak cocok.", "error")
                return redirect(url_for('public.home'))
            
            user.set_password(password)
            changes_made = True
        
        # Only commit if there are actual changes
        if changes_made:
            db.session.commit()
            
            # Update session data with new values
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'perpus_id': user.perpus_id,
                'is_verified': user.is_verified
            }
            SessionManager.set_user_session(user_data, 'user')
            
            flash("Profil berhasil diperbarui.", "success")
        else:
            flash("Tidak ada perubahan yang disimpan.", "info")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        flash("Terjadi kesalahan saat memperbarui profil.", "error")
    
    return redirect(url_for('public.home'))


# --- Rute Alur Donasi ---

@bp.route('/formulir-donasi', methods=['GET', 'POST'])
def formulir_donasi():
    if not SessionManager.is_logged_in('user'):
        flash("Silakan login terlebih dahulu untuk berdonasi.", "warning")
        return redirect(url_for('public.login'))

    # jika masih ada donasi draft, redirect ke halaman konfirmasi dengan toast
    last_invoice = session.get('last_invoice')
    if last_invoice:
        draft = Donasi.query.filter_by(invoice=last_invoice, status='draft').first()
        if draft:
            flash("Silakan lengkapi berkas pengiriman Anda", "warning")
            return redirect(url_for('public.konfirmasi_donasi', invoice=last_invoice))

    user_id = SessionManager.get_current_user_id('user')
    user = User.query.get(user_id)
    subjek_list = SubjekBuku.query.all()

    if request.method == 'POST':
        if not request.form.get('setuju_syarat') or not request.form.get('setuju_pengiriman'):
            flash("Anda harus menyetujui semua persyaratan untuk melanjutkan.", "error")
            return redirect(url_for('public.formulir_donasi'))
        # generate invoice: DNSI + NAMADEPAN + 6-digit random, pastikan unik
        nama_depan = user.full_name.split()[0].upper()
        while True:
            rand6 = ''.join(random.choices('0123456789', k=6))
            invoice = f"DNSI{nama_depan}{rand6}"
            if not Donasi.query.filter_by(invoice=invoice).first():
                break

        donasi = Donasi(
            user_id=user_id,
            invoice=invoice,
            whatsapp=request.form['whatsapp'],
            metode=request.form['metode_pengiriman'],
            notes=request.form.get('notes', ''),
            status='draft'
        )
        db.session.add(donasi)
        db.session.commit()
        
        # Process subjek entries with multiple judul per subjek
        subjek_list_form = request.form.getlist('subjek_buku[]')
        
        for idx, subjek_id in enumerate(subjek_list_form):
            if subjek_id:
                # Get judul_buku and jumlah_eksemplar for this subjek
                judul_list = request.form.getlist(f'judul_buku_{idx}[]')
                jumlah_list = request.form.getlist(f'jumlah_eksemplar_{idx}[]')
                
                for judul, jumlah in zip(judul_list, jumlah_list):
                    if judul and jumlah and jumlah.isdigit():
                        db.session.add(DetailDonasi(
                            donasi_id=donasi.id,
                            subjek_id=int(subjek_id),
                            judul_buku=judul.strip(),
                            jumlah=int(jumlah)
                        ))
        db.session.commit()

        session['last_invoice'] = invoice
        return redirect(url_for('public.konfirmasi_donasi', invoice=invoice))

    return render_template('pengguna/form_donasi.html', user=user, subjek_list=subjek_list)

@bp.route('/konfirmasi-donasi/<invoice>', methods=['GET', 'POST'])
def konfirmasi_donasi(invoice):
    if not SessionManager.is_logged_in('user'):
        return redirect(url_for('public.login'))
    donasi = Donasi.query.filter_by(invoice=invoice).first_or_404()

    if request.method == 'POST':
        file = request.files.get('bukti_resi')
        sampul_file = request.files.get('sampul_buku')
        tgl = request.form.get('tanggal_pengiriman')
        
        # Validate bukti pengiriman file
        if not file or file.filename == '':
            flash("File bukti pengiriman harus diunggah.", "error")
            return redirect(url_for('public.konfirmasi_donasi', invoice=invoice))
        
        if not allowed_file(file.filename):
            flash("File bukti pengiriman harus berformat JPG, JPEG, atau PNG.", "error")
            return redirect(url_for('public.konfirmasi_donasi', invoice=invoice))
        
        # Validate sampul buku file
        if not sampul_file or sampul_file.filename == '':
            flash("File sampul buku harus diunggah.", "error")
            return redirect(url_for('public.konfirmasi_donasi', invoice=invoice))
        
        if not allowed_file(sampul_file.filename):
            flash("File sampul buku harus berformat JPG, JPEG, atau PNG.", "error")
            return redirect(url_for('public.konfirmasi_donasi', invoice=invoice))

        # process bukti pengiriman
        orig_filename = secure_filename(file.filename)
        ext = orig_filename.rsplit('.', 1)[1].lower()
        hash_input = f"{orig_filename}{datetime.utcnow().timestamp()}"
        hashed_name = hashlib.sha256(hash_input.encode()).hexdigest()
        filename = f"{hashed_name}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'public', 'bukti-pengiriman')
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        donasi.bukti_pengiriman = filename

        # process sampul buku
        orig_sampul = secure_filename(sampul_file.filename)
        ext_s = orig_sampul.rsplit('.', 1)[1].lower()
        hash_input_s = f"{orig_sampul}{datetime.utcnow().timestamp()}"
        hashed_s = hashlib.sha256(hash_input_s.encode()).hexdigest()
        sampul_name = f"{hashed_s}.{ext_s}"
        sampul_dir = os.path.join(current_app.root_path, 'static', 'public', 'sampul-buku')
        os.makedirs(sampul_dir, exist_ok=True)
        sampul_file.save(os.path.join(sampul_dir, sampul_name))
        donasi.sampul_buku = sampul_name

        donasi.tanggal_pengiriman = datetime.strptime(tgl, '%Y-%m-%d')
        donasi.status = 'pending'
        db.session.commit()
        session.pop('last_invoice', None)
        return redirect(url_for('public.konfirmasi_berhasil', invoice=donasi.invoice))

    return render_template('pengguna/konfirmasi_donasi.html', donasi=donasi)

@bp.route('/batal-donasi/<invoice>', methods=['POST'])
def batal_donasi(invoice):
    donasi = Donasi.query.filter_by(invoice=invoice).first_or_404()
    DetailDonasi.query.filter_by(donasi_id=donasi.id).delete()
    db.session.delete(donasi)
    db.session.commit()
    session.pop('last_invoice', None)
    flash("Berhasil membatalkan donasi", "success")
    return redirect(url_for('public.formulir_donasi'))

@bp.route('/konfirmasi-berhasil/<invoice>')
def konfirmasi_berhasil(invoice):
    if not SessionManager.is_logged_in('user'):
        return redirect(url_for('public.home'))
    donasi = Donasi.query.filter_by(invoice=invoice).first_or_404()
    if donasi.user_id != SessionManager.get_current_user_id('user'):
        flash("Anda tidak memiliki akses ke halaman ini.", "error")
        return redirect(url_for('public.home'))
    return render_template('pengguna/konfirmasi_berhasil.html', invoice=invoice)

@bp.route('/unduh-bukti-donasi/<invoice>')
def generate_pdf(invoice):
    # require user login
    if not SessionManager.is_logged_in('user'):
        flash("Silakan login terlebih dahulu.", "warning")
        return redirect(url_for('public.login'))
    # fetch donation by invoice and verify owner
    donasi = Donasi.query.filter_by(invoice=invoice).first_or_404()
    if donasi.user_id != SessionManager.get_current_user_id('user'):
        flash("Anda tidak memiliki akses ke halaman ini.", "error")
        return redirect(url_for('public.home'))
    # get detail items with proper relationship
    raw_details = DetailDonasi.query.filter_by(donasi_id=donasi.id).all()
    detail_buku = []
    for d in raw_details:
        # use the relationship to get the actual subject name
        detail_buku.append({
            'subjek_nama': d.subjek.nama if d.subjek else 'Unknown',
            'jumlah': d.jumlah
        })

    bukti = donasi.bukti_pengiriman
    # build a readable donation number
    nomor_donasi = f"DN-{donasi.tanggal_pengiriman.strftime('%Y%m%d')}-{str(donasi.id).zfill(3)}"
    # absolut path ke logo
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo2.png')
    # render PDF HTML
    rendered = render_template(
        'pengguna/bukti_donasi_pdf.html',
        donasi=donasi,
        detail_buku=detail_buku,
        bukti=bukti,
        nomor_donasi=nomor_donasi,
        logo_path=logo_path
    )
    # write PDF to disk
    PDF_FOLDER = os.path.join(current_app.root_path, 'static', 'pdf')
    os.makedirs(PDF_FOLDER, exist_ok=True)
    pdf_path = os.path.join(PDF_FOLDER, f'bukti_donasi_{invoice}.pdf')
    # jika file sudah ada, tidak perlu generate ulang
    if not os.path.exists(pdf_path):
        # Detect operating system and set wkhtmltopdf path accordingly
        system_os = platform.system().lower()
        
        if system_os == 'windows':
            # Windows path
            wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        else:
            # Linux/Ubuntu path (usually installed via apt-get)
            wkhtmltopdf_path = '/usr/bin/wkhtmltopdf'
            
        # Check if wkhtmltopdf exists, if not try alternative paths
        if not os.path.exists(wkhtmltopdf_path):
            if system_os == 'linux':
                # Try alternative Linux paths
                alternative_paths = [
                    '/usr/local/bin/wkhtmltopdf',
                    '/opt/wkhtmltopdf/bin/wkhtmltopdf',
                    'wkhtmltopdf'  # Let system find it in PATH
                ]
                for alt_path in alternative_paths:
                    if alt_path == 'wkhtmltopdf' or os.path.exists(alt_path):
                        wkhtmltopdf_path = alt_path
                        break
        
        try:
            # Configure pdfkit with detected path
            if wkhtmltopdf_path == 'wkhtmltopdf':
                # Let pdfkit use system PATH
                config = None
            else:
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            
            # PDF generation options
            options = {
                'enable-local-file-access': '',
                'page-size': 'A4',
                'margin-top': '2cm',
                'margin-right': '2cm',
                'margin-bottom': '2cm',
                'margin-left': '2cm',
                'encoding': 'UTF-8',
                'no-outline': None
            }
            
            pdfkit.from_string(
                rendered,
                pdf_path,
                configuration=config,
                options=options
            )
            
        except Exception as e:
            # If PDF generation fails, log error and show user-friendly message
            current_app.logger.error(f"PDF generation failed: {str(e)}")
            flash("Maaf, terjadi kesalahan saat membuat PDF. Silakan coba lagi nanti.", "error")
            return redirect(url_for('public.konfirmasi_berhasil', invoice=donasi.invoice))
    
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"bukti_donasi_{invoice}.pdf"
    )

@bp.route('/semua-berita')
def semua_berita():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 6  # 6 news per page
    
    # Get search parameter
    search = request.args.get('search', '', type=str)
    
    # Build query
    query = db.session.query(
        KegiatanPerpus.id,
        KegiatanPerpus.nama_kegiatan,
        KegiatanPerpus.tanggal_kegiatan,
        KegiatanPerpus.deskripsi_kegiatan,
        KegiatanPerpus.foto_kegiatan,
        User.full_name.label('author_name'),
        PerpusDesa.nama.label('perpus_name'),
        PerpusDesa.kecamatan.label('kecamatan_name')
    ).join(
        User, KegiatanPerpus.user_id == User.id
    ).join(
        PerpusDesa, KegiatanPerpus.perpus_id == PerpusDesa.id
    ).filter(
        KegiatanPerpus.status == 'active'
    )
    
    # Add search filter if provided
    if search:
        query = query.filter(
            or_(
                KegiatanPerpus.nama_kegiatan.ilike(f'%{search}%'),
                KegiatanPerpus.deskripsi_kegiatan.ilike(f'%{search}%'),
                PerpusDesa.nama.ilike(f'%{search}%')
            )
        )
    
    # Order by date and paginate
    pagination = query.order_by(
        KegiatanPerpus.tanggal_kegiatan.desc()
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Format news data
    news_data = []
    for news in pagination.items:
        # Create excerpt from description
        excerpt = re.sub(r'<[^>]+>', '', news.deskripsi_kegiatan)
        if len(excerpt) > 150:
            excerpt = excerpt[:150] + '...'
        
        news_data.append({
            'id': news.id,
            'title': news.nama_kegiatan,
            'author': format_author_name(news.author_name),
            'date': format_indonesian_date(news.tanggal_kegiatan),
            'image': f'public/kegiatan-perpus/{news.foto_kegiatan}' if news.foto_kegiatan else 'images/library.jpg',
            'excerpt': excerpt,
            'slug': create_slug(news.nama_kegiatan),
            'perpus_slug': create_perpus_slug(news.perpus_name, news.kecamatan_name)
        })
    
    return render_template('pengguna/semua_berita.html', 
                         news_list=news_data,
                         pagination=pagination,
                         search=search)

@bp.route('/berita/<perpus_slug>/<slug>')
def detail_berita(perpus_slug, slug):
    # Find news by perpus_slug and slug
    all_news = db.session.query(
        KegiatanPerpus.id,
        KegiatanPerpus.nama_kegiatan,
        KegiatanPerpus.tanggal_kegiatan,
        KegiatanPerpus.deskripsi_kegiatan,
        KegiatanPerpus.foto_kegiatan,
        KegiatanPerpus.lokasi_kegiatan,
        User.full_name.label('author_name'),
        PerpusDesa.nama.label('perpus_name'),
        PerpusDesa.kecamatan.label('kecamatan_name')
    ).join(
        User, KegiatanPerpus.user_id == User.id
    ).join(
        PerpusDesa, KegiatanPerpus.perpus_id == PerpusDesa.id
    ).filter(
        KegiatanPerpus.status == 'active'
    ).all()
    
    # Find matching news by perpus_slug and slug
    current_news = None
    for news in all_news:
        news_perpus_slug = create_perpus_slug(news.perpus_name, news.kecamatan_name)
        news_slug = create_slug(news.nama_kegiatan)
        if news_perpus_slug == perpus_slug and news_slug == slug:
            current_news = news
            break
    
    if not current_news:
        flash("Berita tidak ditemukan.", "error")
        return redirect(url_for('public.home'))
    
    # Format current news data
    news_data = {
        'id': current_news.id,
        'title': current_news.nama_kegiatan,
        'author': format_author_name(current_news.author_name),
        'date': format_indonesian_date(current_news.tanggal_kegiatan),
        'image': f'public/kegiatan-perpus/{current_news.foto_kegiatan}' if current_news.foto_kegiatan else 'images/library.jpg',
        'content': current_news.deskripsi_kegiatan,
        'location': current_news.lokasi_kegiatan,
        'slug': slug,
        'perpus_slug': perpus_slug,
        'perpus_name': current_news.perpus_name
    }
    
    # Get related news (3 other recent news excluding current)
    related_news = []
    other_news = [news for news in all_news if news.id != current_news.id]
    other_news.sort(key=lambda x: x.tanggal_kegiatan, reverse=True)
    
    for news in other_news[:3]:
        excerpt = re.sub(r'<[^>]+>', '', news.deskripsi_kegiatan)
        if len(excerpt) > 100:
            excerpt = excerpt[:100] + '...'
        
        related_news.append({
            'id': news.id,
            'title': news.nama_kegiatan,
            'author': format_author_name(news.author_name),
            'date': format_indonesian_date(news.tanggal_kegiatan),
            'image': f'public/kegiatan-perpus/{news.foto_kegiatan}' if news.foto_kegiatan else 'images/library.jpg',
            'excerpt': excerpt,
            'slug': create_slug(news.nama_kegiatan),
            'perpus_slug': create_perpus_slug(news.perpus_name, news.kecamatan_name)
        })
    
    return render_template('pengguna/detail_berita.html', 
                         news=news_data,
                         related_news=related_news)

@bp.route('/resi/<invoice>')
def view_resi(invoice):
    """Display receipt image for a specific donation invoice"""
    donasi = Donasi.query.filter_by(invoice=invoice).first_or_404()
    
    if not donasi.bukti_pengiriman:
        flash("Bukti pengiriman tidak ditemukan.", "error")
        return redirect(url_for('public.home'))
    
    # Serve the image from bukti-pengiriman folder
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'public', 'bukti-pengiriman'),
        donasi.bukti_pengiriman
    )

@bp.route('/api/check-perpus-detail/<int:perpus_id>')
def check_perpus_detail(perpus_id):
    """API endpoint to check if perpus has detail profile"""
    try:
        # Get perpus info for debugging
        perpus = PerpusDesa.query.get(perpus_id)
        if not perpus:
            current_app.logger.debug(f"No perpus found for ID: {perpus_id}")
            return jsonify({'has_detail': False, 'reason': 'perpus_not_found'})
        
        # Log the perpus name and expected slug
        expected_slug = create_perpus_slug(perpus.nama, perpus.kecamatan)
        current_app.logger.debug(f"Checking perpus '{perpus.nama}' in '{perpus.kecamatan}' (ID: {perpus_id}) with expected slug: '{expected_slug}'")
        
        detail = DetailPerpus.query.filter_by(perpus_id=perpus_id).first()
        
        # Check if detail exists
        if not detail:
            current_app.logger.debug(f"No detail found for perpus_id: {perpus_id} ('{perpus.nama}')")
            return jsonify({'has_detail': False, 'reason': 'no_detail_record'})
        
        # Check if essential fields are filled - be more flexible with validation
        required_fields = [
            detail.penanggung_jawab,
            detail.deskripsi,
            detail.latar_belakang
        ]
        
        # Check each field more carefully
        valid_fields = []
        field_names = ['penanggung_jawab', 'deskripsi', 'latar_belakang']
        for i, field in enumerate(required_fields):
            is_valid = field is not None and str(field).strip() != '' and str(field).strip().lower() != 'null'
            valid_fields.append(is_valid)
            current_app.logger.debug(f"Field {field_names[i]}: '{field}' -> Valid: {is_valid}")
        
        # Check if all required fields have values
        has_complete_detail = all(valid_fields)
        
        current_app.logger.debug(f"Perpus '{perpus.nama}' (ID {perpus_id}): has_complete_detail = {has_complete_detail}")
        current_app.logger.debug(f"Field validation summary: {dict(zip(field_names, valid_fields))}")
        
        return jsonify({
            'has_detail': has_complete_detail,
            'perpus_name': perpus.nama,
            'kecamatan_name': perpus.kecamatan,
            'expected_slug': expected_slug,
            'debug_info': {
                'perpus_id': perpus_id,
                'perpus_name': perpus.nama,
                'kecamatan_name': perpus.kecamatan,
                'detail_exists': True,
                'penanggung_jawab_valid': valid_fields[0],
                'penanggung_jawab_value': str(detail.penanggung_jawab) if detail.penanggung_jawab else 'NULL',
                'deskripsi_valid': valid_fields[1],
                'deskripsi_value': str(detail.deskripsi)[:50] + '...' if detail.deskripsi and len(str(detail.deskripsi)) > 50 else str(detail.deskripsi) if detail.deskripsi else 'NULL',
                'latar_belakang_valid': valid_fields[2],
                'latar_belakang_value': str(detail.latar_belakang)[:50] + '...' if detail.latar_belakang and len(str(detail.latar_belakang)) > 50 else str(detail.latar_belakang) if detail.latar_belakang else 'NULL'
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking perpus detail for ID {perpus_id}: {str(e)}")
        return jsonify({'has_detail': False, 'error': str(e)}), 500

@bp.route('/perpusdes/<slug>')
def detail_perpusdes(slug):
    """Display detailed profile of a specific perpustakaan desa"""
    # Find perpus by slug
    all_perpus = PerpusDesa.query.all()
    
    current_perpus = None
    for perpus in all_perpus:
        perpus_slug = create_perpus_slug(perpus.nama, perpus.kecamatan)
        if perpus_slug == slug:
            current_perpus = perpus
            break
    
    if not current_perpus:
        flash("Perpustakaan tidak ditemukan.", "error")
        return redirect(url_for('public.perpusdes'))
    
    # Get perpus detail
    detail = DetailPerpus.query.filter_by(perpus_id=current_perpus.id).first()
    
    if not detail:
        flash("Profil perpustakaan belum tersedia.", "warning")
        return redirect(url_for('public.perpusdes'))
    
    # Get related news for this perpus
    related_news_query = db.session.query(
        KegiatanPerpus.id,
        KegiatanPerpus.nama_kegiatan,
        KegiatanPerpus.tanggal_kegiatan,
        KegiatanPerpus.deskripsi_kegiatan,
        KegiatanPerpus.foto_kegiatan,
        User.full_name.label('author_name'),
        PerpusDesa.nama.label('perpus_name'),
        PerpusDesa.kecamatan.label('kecamatan_name')
    ).join(
        User, KegiatanPerpus.user_id == User.id
    ).join(
        PerpusDesa, KegiatanPerpus.perpus_id == PerpusDesa.id
    ).filter(
        KegiatanPerpus.status == 'active',
        KegiatanPerpus.perpus_id == current_perpus.id
    ).order_by(
        KegiatanPerpus.tanggal_kegiatan.desc()
    ).all()
    
    # Format related news data
    related_news = []
    for news in related_news_query:
        # Create excerpt from description
        excerpt = re.sub(r'<[^>]+>', '', news.deskripsi_kegiatan)
        if len(excerpt) > 150:
            excerpt = excerpt[:150] + '...'
        
        related_news.append({
            'id': news.id,
            'title': news.nama_kegiatan,
            'author': format_author_name(news.author_name),
            'date': format_indonesian_date(news.tanggal_kegiatan),
            'image': f'public/kegiatan-perpus/{news.foto_kegiatan}' if news.foto_kegiatan else 'images/library.jpg',
            'excerpt': excerpt,
            'slug': create_slug(news.nama_kegiatan),
            'perpus_slug': create_perpus_slug(news.perpus_name, news.kecamatan_name)
        })
    
    return render_template('pengguna/detail_perpusdes.html', 
                         perpus=current_perpus,
                         detail=detail,
                         related_news=related_news)
    
# route untuk ke halaman Kategori Buku
@bp.route('/kategori-buku')
def kategori_buku():
    return render_template('pengguna/kategori_buku.html')

# Register a Jinja filter for Indonesian date formatting
@bp.app_template_filter('format_id_date')
def format_id_date_filter(date_obj):
    return format_indonesian_date(date_obj)

# Route untuk halaman Analisis Statistik (publik)
@bp.route('/analisis-statistik')
def analisis_statistik():
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
    
    # Calculate statistics
    # Total buku diterima (confirmed donations only)
    total_buku_diterima = db.session.query(func.sum(DetailDonasi.diterima))\
        .join(Donasi, Donasi.id == DetailDonasi.donasi_id)\
        .filter(Donasi.status == 'confirmed')\
        .scalar() or 0
    
    # Total buku tersalurkan (from distribution records)
    total_buku_tersalurkan = db.session.query(func.sum(DetailRiwayatDistribusi.jumlah))\
        .scalar() or 0
    
    # Top 5 subjects by total donations
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
    
    # Top 5 libraries by total books received
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
        'total_buku_tersalurkan': total_buku_tersalurkan
    }
    
    return render_template('pengguna/analisis_statistik.html',
                         stats=stats,
                         available_years=available_years,
                         current_year=current_year,
                         top_subjects=top_subjects,
                         top_libraries=top_libraries)

# API Endpoints for Public Statistics Charts
@bp.route('/api/public/donation-data/<int:year>')
def api_public_donation_data(year):
    """Get donation data by subject for specified year (public access)"""
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

@bp.route('/api/public/distribution-data/<int:year>')
def api_public_distribution_data(year):
    """Get distribution data by month for specified year (public access)"""
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