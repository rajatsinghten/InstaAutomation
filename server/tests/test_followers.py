def test_followers_list(client, auth_headers):
    response = client.get("/api/v1/followers/list", headers=auth_headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["total_count"] > 0
    assert isinstance(payload["followers"], list)


def test_unfollowers_and_stats(client, auth_headers):
    unfollowers_response = client.get(
        "/api/v1/followers/unfollowers", headers=auth_headers
    )
    assert unfollowers_response.status_code == 200

    stats_response = client.get("/api/v1/followers/stats", headers=auth_headers)
    assert stats_response.status_code == 200

    stats = stats_response.json()
    assert stats["total_followers"] >= 0
    assert stats["total_following"] >= 0
