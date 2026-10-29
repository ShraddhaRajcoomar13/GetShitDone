def test_full_flow(auth_client):
    g = auth_client.post("/api/goals", json={
        "title": "Weekly goal", "week_start": "2025-01-06"
    }).json()
    t = auth_client.post("/api/tasks", json={
        "title": "Task A", "goal_id": g["id"], "estimated_minutes": 30
    }).json()
    auth_client.post("/api/schedule/availability", json={"date": "2025-01-06", "available_minutes": 120})
    plan = auth_client.get("/api/schedule/suggest?week_start=2025-01-06").json()
    assert any(s["task_id"] == t["id"] for s in plan["scheduled"])
    auth_client.post("/api/schedule/apply?week_start=2025-01-06")
    done = auth_client.post(f"/api/tasks/{t['id']}/complete").json()
    assert done["status"] == "completed"
    dash = auth_client.get("/api/dashboard").json()
    assert "agent_summary" in dash
    # ideas
    idea = auth_client.post("/api/ideas", json={"content": "Try CSS grid"}).json()
    converted = auth_client.post(f"/api/ideas/{idea['id']}/to-task").json()
    assert "task_id" in converted