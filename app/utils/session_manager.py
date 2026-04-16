from flask import session

class SessionManager:
    """Manage separate sessions for different user roles"""
    
    # Session keys for different roles
    USER_SESSION_KEY = 'user_session'
    ADMIN_SESSION_KEY = 'admin_session'
    SUPERADMIN_SESSION_KEY = 'superadmin_session'
    
    @staticmethod
    def get_session_key(role):
        """Get session key based on role"""
        if role == 'user':
            return SessionManager.USER_SESSION_KEY
        elif role == 'admin':
            return SessionManager.ADMIN_SESSION_KEY
        elif role == 'superadmin':
            return SessionManager.SUPERADMIN_SESSION_KEY
        return None
    
    @staticmethod
    def set_user_session(user_data, role='user'):
        """Set session data for specific role"""
        session_key = SessionManager.get_session_key(role)
        if session_key:
            session[session_key] = {
                'user_id': user_data.get('user_id'),
                'username': user_data.get('username'),
                'full_name': user_data.get('full_name'),
                'email': user_data.get('email'),
                'role': role,
                'perpus_id': user_data.get('perpus_id'),
                'is_verified': user_data.get('is_verified', True)
            }
            # Don't clear other sessions - allow multiple roles to be logged in
    
    @staticmethod
    def get_user_session(role='user'):
        """Get session data for specific role"""
        session_key = SessionManager.get_session_key(role)
        if session_key and session_key in session:
            return session[session_key]
        return None
    
    @staticmethod
    def clear_user_session(role='user'):
        """Clear session for specific role"""
        session_key = SessionManager.get_session_key(role)
        if session_key and session_key in session:
            session.pop(session_key, None)
    
    @staticmethod
    def clear_other_sessions(current_role):
        """Clear sessions of other roles"""
        all_roles = ['user', 'admin', 'superadmin']
        for role in all_roles:
            if role != current_role:
                SessionManager.clear_user_session(role)
    
    @staticmethod
    def clear_all_sessions():
        """Clear all role sessions"""
        session.pop(SessionManager.USER_SESSION_KEY, None)
        session.pop(SessionManager.ADMIN_SESSION_KEY, None)
        session.pop(SessionManager.SUPERADMIN_SESSION_KEY, None)
    
    @staticmethod
    def is_logged_in(role='user'):
        """Check if user is logged in for specific role"""
        user_session = SessionManager.get_user_session(role)
        return user_session is not None and user_session.get('role') == role
    
    @staticmethod
    def get_current_user_id(role='user'):
        """Get current user ID for specific role"""
        user_session = SessionManager.get_user_session(role)
        return user_session.get('user_id') if user_session else None
    
    @staticmethod
    def get_current_username(role='user'):
        """Get current username for specific role"""
        user_session = SessionManager.get_user_session(role)
        return user_session.get('username') if user_session else None
    
    @staticmethod
    def get_current_full_name(role='user'):
        """Get current full name for specific role"""
        user_session = SessionManager.get_user_session(role)
        return user_session.get('full_name') if user_session else None
    
    @staticmethod
    def get_current_perpus_id(role='admin'):
        """Get current perpus ID for admin role"""
        user_session = SessionManager.get_user_session(role)
        return user_session.get('perpus_id') if user_session else None
    
    @staticmethod
    def is_any_user_logged_in():
        """Check if any user role is logged in"""
        return (SessionManager.is_logged_in('user') or 
                SessionManager.is_logged_in('admin') or 
                SessionManager.is_logged_in('superadmin'))
    
    @staticmethod
    def get_any_user_session():
        """Get session data for any logged in user, prioritizing user > admin > superadmin"""
        if SessionManager.is_logged_in('user'):
            return SessionManager.get_user_session('user')
        elif SessionManager.is_logged_in('admin'):
            return SessionManager.get_user_session('admin')
        elif SessionManager.is_logged_in('superadmin'):
            return SessionManager.get_user_session('superadmin')
        return None

    @staticmethod
    def get_any_user_data(key):
        """Get specific data key for any logged in user"""
        user_session = SessionManager.get_any_user_session()
        return user_session.get(key) if user_session else None

    @staticmethod
    def get_specific_user_data(key, role='user'):
        """Get specific data key for specific role"""
        user_session = SessionManager.get_user_session(role)
        return user_session.get(key) if user_session else None

# Backward compatibility for existing code
def get_session_data(role='user'):
    """Get session data - backward compatibility function"""
    return SessionManager.get_user_session(role)

def set_session_data(user_data, role='user'):
    """Set session data - backward compatibility function"""
    SessionManager.set_user_session(user_data, role)

def clear_session_data(role='user'):
    """Clear session data - backward compatibility function"""
    SessionManager.clear_user_session(role)
