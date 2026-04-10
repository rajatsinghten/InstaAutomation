def test_login_status_logout_flow(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo.user", "password": "demo-password"},
    )
    assert login_response.status_code == 200

    payload = login_response.json()
    token = payload["access_token"]

    status_response = client.get(
        "/api/v1/auth/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["authenticated"] is True

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True
