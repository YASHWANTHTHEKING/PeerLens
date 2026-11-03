def test_chat_requires_an_api_key(client):
    response = client.post("/chat", json={"message": "Summarize the report."})

    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]


def test_chat_rejects_empty_messages(client):
    response = client.post("/chat", json={"message": " "})

    assert response.status_code == 422


def test_stream_requires_an_api_key(client):
    response = client.post("/chat/stream", json={"message": "Summarize the report."})

    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]
