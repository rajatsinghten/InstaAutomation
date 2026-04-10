def test_download_post(client, auth_headers):
    response = client.post(
        "/api/v1/posts/download",
        headers=auth_headers,
        json={"url": "https://www.instagram.com/p/ABC123xyz/"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["shortcode"] == "ABC123xyz"
    assert payload["media_url"].startswith("https://")


def test_download_reel(client, auth_headers):
    response = client.post(
        "/api/v1/posts/download",
        headers=auth_headers,
        json={"url": "https://www.instagram.com/reel/XYZ987abc/"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["shortcode"] == "XYZ987abc"
    assert payload["media_url"]
