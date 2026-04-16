from functools import wraps
from flask import session, redirect, url_for, flash, request
from .session_manager import SessionManager

def login_required(role='user'):
    """Decorator to require login for specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not SessionManager.is_logged_in(role):
                flash('Silakan login terlebih dahulu.', 'error')
                if role == 'admin':
                    return redirect(url_for('admin.login'))
                elif role == 'superadmin':
                    return redirect(url_for('superadmin.login'))
                else:
                    return redirect(url_for('public.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SessionManager.is_logged_in('admin'):
            flash('Akses ditolak. Silakan login sebagai admin.', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    """Decorator to require superadmin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SessionManager.is_logged_in('superadmin'):
            flash('Akses ditolak. Silakan login sebagai super admin.', 'error')
            return redirect(url_for('superadmin.login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SessionManager.is_logged_in('user'):
            flash('Silakan login terlebih dahulu.', 'error')
            return redirect(url_for('public.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_session = SessionManager.get_user_session(required_role)
            if not user_session or user_session.get('role') != required_role:
                flash(f'Akses ditolak. Diperlukan role {required_role}.', 'error')
                if required_role == 'admin':
                    return redirect(url_for('admin.login'))
                elif required_role == 'superadmin':
                    return redirect(url_for('superadmin.login'))
                else:
                    return redirect(url_for('public.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Backward compatibility
def requires_login(f):
    """Backward compatibility for user login requirement"""
    return login_required('user')(f)

def requires_admin(f):
    """Backward compatibility for admin login requirement"""
    return admin_required(f)

def requires_superadmin(f):
    """Backward compatibility for superadmin login requirement"""
    return superadmin_required(f)
