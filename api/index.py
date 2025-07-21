from vercel_python_wsgi import make_lambda_handler
from src.core.wsgi import application

handler = make_lambda_handler(application)