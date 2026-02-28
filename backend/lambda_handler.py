"""
AWS Lambda entry point.
Mangum wraps the Flask WSGI app so Lambda can invoke it via API Gateway.
"""
from mangum import Mangum
from app import app

handler = Mangum(app, lifespan="off")
