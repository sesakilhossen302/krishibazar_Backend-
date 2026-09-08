from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.get("/")
print("Root Endpoint Response:", response.status_code, response.json())

health_response = client.get("/health")
print("Health Endpoint Response:", health_response.status_code, health_response.json())

print("Backend API test completed successfully!")
