"""Exercise the built container through the public frontend and its API proxy."""
import json
import time
import urllib.request

base = "http://127.0.0.1:10000"
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(base + "/api/health", timeout=3) as response:
            if json.load(response).get("status") == "ok":
                break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("Container did not become ready")
for route in ["/", "/signup", "/login", "/admin"]:
    with urllib.request.urlopen(base + route, timeout=10) as response:
        assert response.status == 200
        assert "HackAMatch" in response.read().decode()
with urllib.request.urlopen(base + "/api/public/status", timeout=5) as response:
    status = json.load(response)
    assert status["team_size"] == 3 and status["email_enabled"] is False
payload = json.dumps({"email": "smoke@example.test", "password": "Synthetic-smoke-pass-938!"}).encode()
request = urllib.request.Request(base + "/api/auth/signup", data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=10) as response:
    assert response.status == 200 and json.load(response)["email_enabled"] is False
print("Container smoke test passed: migrations, frontend, API proxy, database and signup")
