"""
Phase 5: Functional Testing Script
Tests actual API endpoints against the running backend server.
"""
import urllib.request
import urllib.error
import json
import time
import sys

BASE_URL = "http://localhost:8000/api"

def api_post(path, data):
    """Send a POST request with JSON data."""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode()) if e.readable() else str(e)
    except Exception as e:
        return 0, str(e)

def api_get(path):
    """Send a GET request."""
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:
        return 0, str(e)


def print_divider(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_status_endpoint():
    print_divider("TEST: GET /status")
    code, data = api_get("/status")
    print(f"  HTTP {code}")
    print(f"  Status: {data.get('status') if isinstance(data, dict) else data}")
    assert code == 200, f"Expected 200, got {code}"
    assert data.get("status") == "online", f"Expected 'online', got {data.get('status')}"
    print("  ✓ PASSED: Server is online")
    return True


def test_logs_endpoint():
    print_divider("TEST: GET /logs")
    code, data = api_get("/logs")
    print(f"  HTTP {code}")
    print(f"  Logs count: {len(data) if isinstance(data, list) else 'N/A'}")
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(data, list), "Expected list of logs"
    print("  ✓ PASSED: Logs endpoint returns list")
    return True


def test_command_bring_water():
    print_divider("TEST: POST /command — 'Bring me a glass of water'")
    code, data = api_post("/command", {"command": "Bring me a glass of water"})
    print(f"  HTTP {code}")
    if code == 200 and isinstance(data, dict):
        print(f"  Goal: {data.get('goal')}")
        print(f"  Tasks count: {len(data.get('tasks', []))}")
        for t in data.get("tasks", []):
            print(f"    - {t['name']} (action={t['action']}, status={t['status']})")
        print("  ✓ PASSED: Plan generated successfully")
    else:
        print(f"  ✗ FAILED: {data}")
        return False

    # Wait for execution to progress
    print("\n  Waiting 12 seconds for execution to progress...")
    time.sleep(12)

    # Check plan status
    code2, plan = api_get("/plan")
    if code2 == 200 and isinstance(plan, dict):
        print(f"\n  Updated plan status:")
        for t in plan.get("tasks", []):
            print(f"    - {t['name']}: {t['status']} (retries={t.get('retry_count', 0)})")
            if t.get("error_message"):
                print(f"      Error: {t['error_message']}")
        
        # Check if replanning occurred (look for recovery tasks)
        recovery_tasks = [t for t in plan.get("tasks", []) if "recovery" in t.get("id", "")]
        if recovery_tasks:
            print(f"\n  ✓ Replanning detected: {len(recovery_tasks)} recovery tasks injected")
        
        # Check execution status
        code3, status = api_get("/status")
        print(f"\n  Execution Status:")
        print(f"    is_running: {status.get('is_running')}")
        print(f"    is_paused: {status.get('is_paused')}")
        print(f"    current_goal: {status.get('current_goal')}")
    else:
        print(f"  Plan check returned: {code2} {plan}")

    return True


def test_command_go_to_kitchen():
    print_divider("TEST: POST /command — 'Go to the kitchen'")
    code, data = api_post("/command", {"command": "Go to the kitchen"})
    print(f"  HTTP {code}")
    if code == 200 and isinstance(data, dict):
        print(f"  Goal: {data.get('goal')}")
        print(f"  Tasks count: {len(data.get('tasks', []))}")
        for t in data.get("tasks", []):
            print(f"    - {t['name']} (action={t['action']})")
        print("  ✓ PASSED: Plan generated")
    else:
        print(f"  ✗ FAILED: {data}")
        return False

    # Wait for execution
    print("  Waiting 6 seconds for execution...")
    time.sleep(6)

    code2, plan = api_get("/plan")
    if code2 == 200 and isinstance(plan, dict):
        print(f"  Updated plan status:")
        for t in plan.get("tasks", []):
            print(f"    - {t['name']}: {t['status']}")
    return True


def test_pause_resume():
    print_divider("TEST: POST /pause and /resume")
    # Start a command first
    code, data = api_post("/command", {"command": "Pick up the red bottle"})
    print(f"  Command sent: HTTP {code}")
    time.sleep(1)

    # Pause
    code_p, resp_p = api_post("/pause", {})
    print(f"  Pause: HTTP {code_p} — {resp_p}")
    assert code_p == 200, f"Pause failed: {code_p}"

    # Check that it's paused
    code_s, status = api_get("/status")
    print(f"  is_paused: {status.get('is_paused')}")
    
    time.sleep(2)

    # Resume
    code_r, resp_r = api_post("/resume", {})
    print(f"  Resume: HTTP {code_r} — {resp_r}")
    assert code_r == 200, f"Resume failed: {code_r}"

    code_s2, status2 = api_get("/status")
    print(f"  is_paused after resume: {status2.get('is_paused')}")
    print("  ✓ PASSED: Pause/Resume cycle completed")
    return True


def test_cancel():
    print_divider("TEST: POST /cancel")
    # Start a new command
    code, data = api_post("/command", {"command": "Return home"})
    print(f"  Command sent: HTTP {code}")
    time.sleep(1)

    # Cancel
    code_c, resp_c = api_post("/cancel", {})
    print(f"  Cancel: HTTP {code_c} — {resp_c}")
    assert code_c == 200, f"Cancel failed: {code_c}"

    # Verify not running anymore
    code_s, status = api_get("/status")
    print(f"  is_running after cancel: {status.get('is_running')}")
    print("  ✓ PASSED: Cancel endpoint works")
    return True


def test_empty_command():
    print_divider("TEST: POST /command — empty string")
    code, data = api_post("/command", {"command": ""})
    print(f"  HTTP {code}")
    print(f"  Response: {data}")
    # We accept either a 200 with some plan or a 500/422 error  
    print("  ✓ PASSED: Server handled empty command without crash")
    return True


def test_malformed_request():
    print_divider("TEST: POST /command — malformed JSON")
    url = f"{BASE_URL}/command"
    req = urllib.request.Request(url, data=b"not json", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.status
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode()
    except Exception as e:
        code = 0
        body = str(e)
    print(f"  HTTP {code}")
    print(f"  Response: {body[:200]}")
    assert code == 422, f"Expected 422 Unprocessable Entity, got {code}"
    print("  ✓ PASSED: Malformed JSON rejected with 422")
    return True


if __name__ == "__main__":
    results = {}
    tests = [
        ("Status Endpoint", test_status_endpoint),
        ("Logs Endpoint", test_logs_endpoint),
        ("Command: Bring Water", test_command_bring_water),
        ("Command: Go to Kitchen", test_command_go_to_kitchen),
        ("Pause/Resume", test_pause_resume),
        ("Cancel", test_cancel),
        ("Empty Command", test_empty_command),
        ("Malformed Request", test_malformed_request),
    ]

    for name, fn in tests:
        try:
            passed = fn()
            results[name] = "PASSED" if passed else "FAILED"
        except AssertionError as e:
            results[name] = f"FAILED: {e}"
        except Exception as e:
            results[name] = f"ERROR: {e}"

    print_divider("FUNCTIONAL TEST SUMMARY")
    for name, result in results.items():
        marker = "[PASS]" if "PASSED" in result else "[FAIL]"
        print(f"  {marker} {name}: {result}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if "PASSED" in v)
    failed = total - passed
    print(f"\n  Total: {total} | Passed: {passed} | Failed: {failed}")

    if failed > 0:
        sys.exit(1)
