from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """Application Factory Function"""
    app = Flask(__name__)

    # Load environment variables
    load_dotenv()
    
    # --- Konfigurasi ---
    app.config['SECRET_KEY'] = 'rahasia123@$'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or ('sqlite:///' + os.path.join(basedir, '..', 'instance', 'users.db'))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Email Configuration - Add these configurations
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes', 'on']
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 'yes', 'on']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))
    
    # File Upload Configuration
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads', 'resi')
    instance_path = os.path.join(basedir, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # --- Inisialisasi Ekstensi ---
    db.init_app(app)
    migrate.init_app(app, db)

    # --- Impor & Daftarkan Blueprint dari Controllers ---
    from .controllers import public_routes, admin_routes, superadmin_routes

    app.register_blueprint(public_routes.bp)
    app.register_blueprint(admin_routes.bp, url_prefix='/admin')
    app.register_blueprint(superadmin_routes.bp, url_prefix='/superadmin')

    # --- Impor Model ---
    from . import models

    # Import SessionManager saja
    from .utils.session_manager import SessionManager
    
    # Context processor untuk membuat SessionManager tersedia di semua template
    @app.context_processor
    def inject_session_manager():
        return {
            'SessionManager': SessionManager,
            'is_user_logged_in': lambda: SessionManager.is_logged_in('user'),
            'is_admin_logged_in': lambda: SessionManager.is_logged_in('admin'),
            'is_superadmin_logged_in': lambda: SessionManager.is_logged_in('superadmin')
        }

    return app