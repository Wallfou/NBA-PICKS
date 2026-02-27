"""
AWS Lambda entry point.
Mangum wraps the Flask WSGI app so Lambda can invoke it via API Gateway.
"""
from mangum import Mangum
from app import app

# Lambda handler — API Gateway (HTTP API or REST API) routes requests here
handler = Mangum(app, lifespan="off")
