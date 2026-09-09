import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.get("/")
print("Root Endpoint Response:", response.status_code, response.json())

health_response = client.get("/health")
print("Health Endpoint Response:", health_response.status_code, health_response.json())

users_response = client.get("/api/v1/users/")
print("Users List Response:", users_response.status_code, f"Found {len(users_response.json())} users")

print("Backend API test completed successfully!")
