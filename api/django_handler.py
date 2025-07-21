import os
import sys
from io import StringIO

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Import Django and configure
import django
django.setup()

# Import the WSGI application
from core.wsgi import application

def handler(event, context):
    """
    Vercel serverless function handler for Django
    """
    try:
        # Extract request information from Vercel event
        method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        query_string = event.get('queryStringParameters') or {}
        headers = event.get('headers', {})
        body = event.get('body', '')
        
        # Build query string
        query_params = '&'.join([f"{k}={v}" for k, v in query_string.items()])
        
        # Create WSGI environ
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': query_params,
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)) if body else '0',
            'SERVER_NAME': headers.get('host', 'localhost'),
            'SERVER_PORT': '443',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': StringIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add headers to environ
        for key, value in headers.items():
            key = key.upper().replace('-', '_')
            if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                key = f'HTTP_{key}'
            environ[key] = value
        
        # Response data
        response_data = []
        status = None
        response_headers = []
        
        def start_response(status_line, headers, exc_info=None):
            nonlocal status, response_headers
            status = status_line
            response_headers = headers
        
        # Call the WSGI application
        response = application(environ, start_response)
        
        # Collect response data
        for data in response:
            if data:
                response_data.append(data.decode('utf-8') if isinstance(data, bytes) else data)
        
        # Return Vercel response format
        return {
            'statusCode': int(status.split()[0]),
            'headers': dict(response_headers),
            'body': ''.join(response_data)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Internal Server Error: {str(e)}'
        }