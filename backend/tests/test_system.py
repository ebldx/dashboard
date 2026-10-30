from fastapi.testclient import TestClient


def test_health_reports_database_status(client: TestClient) -> None:
    response = client.get("/api/system/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
