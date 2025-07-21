import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Import Django and configure
import django
django.setup()

# Import the WSGI application
from core.wsgi import application

# Create the handler
from vercel_python_wsgi import make_lambda_handler
handler = make_lambda_handler(application)