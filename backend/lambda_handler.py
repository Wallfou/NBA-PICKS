"""
AWS Lambda entry point.
Flask is WSGI; a2wsgi bridges it to ASGI so Mangum can wrap it for Lambda
"""
from mangum import Mangum
from a2wsgi import WSGIMiddleware
from app import app

handler = Mangum(WSGIMiddleware(app), lifespan="off")
