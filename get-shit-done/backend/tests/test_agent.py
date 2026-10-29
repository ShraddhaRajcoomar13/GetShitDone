def test_agent_creates_tasks_via_decompose(auth_client):
    g = auth_client.post("/api/goals", json={
        "title": "Ship MVP", "week_start": "2025-01-06"
    }).json()
    reply = auth_client.post("/api/agent/chat", json={
        "message": f"Please break down goal {g['id']} into: write spec, build prototype, review"
    }).json()
    assert "tool_calls" in reply
    assert any(tc["name"] == "create_task" for tc in reply["tool_calls"])
    tasks = auth_client.get(f"/api/goals/{g['id']}/tasks").json()
    assert len(tasks) == 3


def test_agent_refuses_when_tool_fails(auth_client):
    reply = auth_client.post("/api/agent/chat", json={
        "message": "complete task 999999"
    }).json()
    results = [tc["result"] for tc in reply["tool_calls"]]
    assert any("ERROR" in r for r in results)