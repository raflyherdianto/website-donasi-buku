from . import db
from flask_login import UserMixin
from sqlalchemy.schema import UniqueConstraint
from datetime import datetime
import pytz
from werkzeug.security import check_password_hash, generate_password_hash

# Helper function to get WIB datetime
def get_wib_datetime():
    return datetime.now(pytz.timezone('Asia/Jakarta'))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)

    perpus_id = db.Column(db.Integer, db.ForeignKey('perpus_desa.id'), nullable=True)
    perpus = db.relationship('PerpusDesa', backref='admin_user')

    __table_args__ = (
        UniqueConstraint('email', name='uq_user_email'),
    )

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)

class Donasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invoice = db.Column(db.String(100))
    whatsapp = db.Column(db.String(20), nullable=False)
    metode = db.Column(db.String(100), nullable=False, default='mandiri')
    notes = db.Column(db.Text, nullable=True)
    tanggal_pengiriman = db.Column(db.DateTime, default=get_wib_datetime)
    sampul_buku = db.Column(db.String(255))
    bukti_pengiriman = db.Column(db.String(255))
    status = db.Column(db.String(20), default='draft')  # draft, pending, confirmed
    sertifikat = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)

    user = db.relationship('User', backref='donasi_list', lazy=True)

    # Tambahkan relasi ke detail donasi
    details = db.relationship('DetailDonasi', backref='donasi', lazy=True)

    @property
    def jumlah_buku(self):
        # total keseluruhan buku diterima dari semua detail
        return sum(d.diterima for d in self.details)

    @property
    def subjek_buku(self):
        # daftar nama subjek, dipisah koma
        return ', '.join(d.subjek.nama for d in self.details)
    
class DetailDonasi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donasi_id = db.Column(db.Integer, db.ForeignKey('donasi.id'), nullable=False)
    subjek_id = db.Column(db.Integer, db.ForeignKey('subjek_buku.id'), nullable=False)
    judul_buku = db.Column(db.String(255), nullable=True)  # Judul buku yang didonasikan
    jumlah = db.Column(db.Integer, nullable=False)  # Jumlah eksemplar per judul
    diterima = db.Column(db.Integer, nullable=False, default=0)  # Jumlah buku yang diterima
    ditolak = db.Column(db.Integer, nullable=False, default=0)  # Jumlah buku yang ditolak
    kuota = db.Column(db.Integer, nullable=False, default=0)  # Jumlah kuota buku
    alasan_ditolak = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)

    # Relationships
    subjek = db.relationship('SubjekBuku', backref='detail_donasi', lazy=True)
class SubjekBuku(db.Model):
    __tablename__ = 'subjek_buku'
    
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    def __repr__(self):
        return f'<SubjekBuku {self.nama}>'

class KebutuhanKoleksi(db.Model):
    __tablename__ = 'kebutuhan_koleksi'
    
    id = db.Column(db.Integer, primary_key=True)
    perpus_id = db.Column(db.Integer, db.ForeignKey('perpus_desa.id'), nullable=False)
    prioritas = db.Column(db.String(20), nullable=False)  # Sangat dibutuhkan, Dibutuhkan
    lokasi = db.Column(db.Text)
    alasan = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    pesan = db.Column(db.Text)
    tanggal_pengajuan = db.Column(db.DateTime, default=get_wib_datetime)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    # Relationships
    perpus = db.relationship('PerpusDesa', backref='kebutuhan_koleksi', lazy=True)
    detail_kebutuhan = db.relationship('DetailKebutuhanKoleksi', backref='kebutuhan_koleksi', lazy=True)
    
    # Properties for template compatibility
    @property
    def subjek_buku(self):
        """Get the first subject from details for template display"""
        if self.detail_kebutuhan:
            return self.detail_kebutuhan[0].subjek
        return None
    
    @property
    def jumlah_buku(self):
        """Get total number of books from all details"""
        return sum(detail.jumlah_buku for detail in self.detail_kebutuhan)
    
    @property
    def subjek_list(self):
        """Get comma-separated list of all subjects"""
        if self.detail_kebutuhan:
            return ', '.join(detail.subjek.nama for detail in self.detail_kebutuhan)
        return ''
    
    def __repr__(self):
        return f'<KebutuhanKoleksi {self.id}>'

class DetailKebutuhanKoleksi(db.Model):
    __tablename__ = 'detail_kebutuhan_koleksi'
    
    id = db.Column(db.Integer, primary_key=True)
    kebutuhan_id = db.Column(db.Integer, db.ForeignKey('kebutuhan_koleksi.id'), nullable=False)
    subjek_id = db.Column(db.Integer, db.ForeignKey('subjek_buku.id'), nullable=False)
    jumlah_buku = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    # Relationships
    subjek = db.relationship('SubjekBuku', backref='detail_kebutuhan_koleksi', lazy=True)
    
    def __repr__(self):
        return f'<DetailKebutuhanKoleksi {self.id}>'

class RiwayatDistribusi(db.Model):
    __tablename__ = 'riwayat_distribusi'
    
    id = db.Column(db.Integer, primary_key=True)
    perpus_id = db.Column(db.Integer, db.ForeignKey('perpus_desa.id'), nullable=False)
    status = db.Column(db.String(20), default='pengiriman')  # pengiriman, diterima
    bukti_foto = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    # Relationships
    perpus = db.relationship('PerpusDesa', backref='riwayat_distribusi', lazy=True)

    # mengembalikan subjek (dari detail pertama) agar template {{ item.subjek_buku.nama }} tidak error
    @property
    def subjek_buku(self):
        try:
            if hasattr(self, 'detail_riwayat_distribusi') and self.detail_riwayat_distribusi:
                first_detail = self.detail_riwayat_distribusi[0]
                if hasattr(first_detail, 'subjek') and first_detail.subjek:
                    return first_detail.subjek
            return None
        except (IndexError, AttributeError, TypeError):
            return None

    # menjumlahkan semua buku di detail distribusi agar template {{ item.jumlah }} bekerja
    @property
    def jumlah(self):
        try:
            if hasattr(self, 'detail_riwayat_distribusi') and self.detail_riwayat_distribusi:
                return sum(
                    getattr(d, 'jumlah', 0) or 0 
                    for d in self.detail_riwayat_distribusi 
                    if hasattr(d, 'jumlah')
                )
            return 0
        except (AttributeError, TypeError):
            return 0

    def __repr__(self):
        return f'<RiwayatDistribusi {self.id}>'

class DetailRiwayatDistribusi(db.Model):
    __tablename__ = 'detail_riwayat_distribusi'
    
    id = db.Column(db.Integer, primary_key=True)
    distribusi_id = db.Column(db.Integer, db.ForeignKey('riwayat_distribusi.id'), nullable=False)
    donasi_id = db.Column(db.Integer, db.ForeignKey('donasi.id'), nullable=False)
    subjek_id = db.Column(db.Integer, db.ForeignKey('subjek_buku.id'), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)

    # Relationships
    distribusi = db.relationship('RiwayatDistribusi', backref='detail_riwayat_distribusi', lazy=True)
    donasi = db.relationship('Donasi', backref='detail_riwayat_distribusi_list', lazy=True)
    subjek = db.relationship('SubjekBuku', backref='detail_riwayat_distribusi', lazy=True)

class Kunjungan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    perpus_id = db.Column(db.Integer, db.ForeignKey('perpus_desa.id'), nullable=True)
    tanggal = db.Column(db.DateTime, default=get_wib_datetime)  # Always stores WIB time
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    perpus = db.relationship('PerpusDesa', backref='kunjungan_list')

class PerpusDesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    kecamatan = db.Column(db.String(100), nullable=False)
    desa = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)

class DetailPerpus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    perpus_id = db.Column(db.Integer, db.ForeignKey('perpus_desa.id'), nullable=False)
    penanggung_jawab = db.Column(db.String(100), nullable=False)
    foto_perpus = db.Column(db.String(255), nullable=True)
    deskripsi = db.Column(db.Text, nullable=False)
    latar_belakang = db.Column(db.String(255), nullable=False)
    jumlah_koleksi = db.Column(db.Integer, nullable=True)
    jumlah_eksemplar = db.Column(db.Integer, nullable=True)
    jam_operasional_mulai = db.Column(db.Time, nullable=True)
    jam_operasional_selesai = db.Column(db.Time, nullable=True)
    koleksi_buku = db.Column(db.String(255), nullable=True)
    lokasi = db.Column(db.Text, nullable=True)  # Will store Google Maps link
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    perpus = db.relationship('PerpusDesa', backref='detail_perpus')

class KegiatanPerpus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    perpus_id = db.Column(db.Integer, db.ForeignKey('perpus_desa.id'), nullable=False)
    nama_kegiatan = db.Column(db.String(200), nullable=False)
    tanggal_kegiatan = db.Column(db.Date, nullable=False)
    deskripsi_kegiatan = db.Column(db.Text, nullable=False)  # HTML content
    lokasi_kegiatan = db.Column(db.String(255), nullable=False)  # Google Maps link (same as detail_perpus.lokasi)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    foto_kegiatan = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, archived
    created_at = db.Column(db.DateTime, default=get_wib_datetime)
    updated_at = db.Column(db.DateTime, default=get_wib_datetime, onupdate=get_wib_datetime)
    
    user = db.relationship('User', backref='kegiatan_perpus_list')
    perpus = db.relationship('PerpusDesa', backref='kegiatan_list')