import os
from dotenv import load_dotenv

# Load environment variables first - before importing the app
load_dotenv()

from app import create_app

# Create Flask app instance
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'on']
    port = int(os.environ.get('FLASK_PORT', 5000))
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    
    print(f"Starting Flask app on {host}:{port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)