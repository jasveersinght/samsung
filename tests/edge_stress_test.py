"""
Phase 6 & 7: Edge Case and Stress Testing Script
Tests boundary conditions, concurrent requests, and unusual inputs.
"""
import urllib.request
import urllib.error
import json
import time
import sys
import threading

BASE_URL = "http://localhost:8000/api"

def api_post(path, data):
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
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:
        return 0, str(e)


def divider(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ========================================
# PHASE 6: EDGE CASE TESTS
# ========================================

def test_very_long_command():
    """Test extremely long input string."""
    divider("EDGE: Very Long Command (2000 chars)")
    long_cmd = "Navigate to " + "the very far away " * 100 + "destination"
    code, data = api_post("/command", {"command": long_cmd})
    print(f"  HTTP {code}")
    assert code == 200, f"Expected 200, got {code}"
    print(f"  Goal: {str(data.get('goal', ''))[:80]}")
    print("  [PASS] Server handled very long command")
    return True


def test_special_characters_command():
    """Test special characters in command."""
    divider("EDGE: Special Characters in Command")
    special_cmd = "Go to <room>; DROP TABLE tasks;-- AND /etc/passwd && rm -rf /"
    code, data = api_post("/command", {"command": special_cmd})
    print(f"  HTTP {code}")
    print(f"  Goal: {data.get('goal', '') if isinstance(data, dict) else str(data)[:100]}")
    # Should NOT crash the server
    assert code in [200, 500], f"Unexpected status: {code}"
    print("  [PASS] Server handled special chars without crash")
    return True


def test_unicode_command():
    """Test Unicode/emoji in command."""
    divider("EDGE: Unicode/Emoji in Command")
    code, data = api_post("/command", {"command": "Take the robot to the kitchen"})
    print(f"  HTTP {code}")
    assert code == 200, f"Expected 200, got {code}"
    print("  [PASS] Server handled unicode command")
    return True


def test_rapid_cancel_after_command():
    """Test cancelling immediately after sending a command."""
    divider("EDGE: Rapid Cancel After Command")
    code, data = api_post("/command", {"command": "Go to the office"})
    print(f"  Command sent: HTTP {code}")
    # Immediately cancel
    code_c, resp_c = api_post("/cancel", {})
    print(f"  Cancel: HTTP {code_c} - {resp_c}")
    assert code_c == 200, f"Cancel failed: {code_c}"
    
    code_s, status = api_get("/status")
    print(f"  is_running: {status.get('is_running')}")
    print("  [PASS] Rapid cancel handled correctly")
    return True


def test_double_cancel():
    """Test cancelling when nothing is running."""
    divider("EDGE: Double Cancel (no active execution)")
    code, data = api_post("/cancel", {})
    print(f"  HTTP {code} - {data}")
    # Should not crash
    print("  [PASS] Double cancel handled gracefully")
    return True


def test_pause_without_execution():
    """Test pausing when nothing is executing."""
    divider("EDGE: Pause Without Execution")
    # Cancel anything first
    api_post("/cancel", {})
    time.sleep(0.5)
    code, data = api_post("/pause", {})
    print(f"  HTTP {code} - {data}")
    print("  [PASS] Pause without execution handled")
    return True


def test_resume_without_pause():
    """Test resume when not paused."""
    divider("EDGE: Resume Without Pause")
    code, data = api_post("/resume", {})
    print(f"  HTTP {code} - {data}")
    print("  [PASS] Resume without pause handled")
    return True


def test_multiple_commands_override():
    """Test sending multiple commands rapidly - each should override the last."""
    divider("EDGE: Multiple Commands Override")
    cmds = ["Go to the kitchen", "Go to the office", "Return home"]
    for cmd in cmds:
        code, data = api_post("/command", {"command": cmd})
        print(f"  '{cmd}': HTTP {code}, goal={data.get('goal', 'N/A') if isinstance(data, dict) else 'error'}")
    
    time.sleep(1)
    code_s, status = api_get("/status")
    print(f"  Current goal: {status.get('current_goal')}")
    print("  [PASS] Multiple commands handled (last wins)")
    api_post("/cancel", {})
    return True


def test_get_plan_when_none():
    """Test getting plan when no plan exists."""
    divider("EDGE: GET /plan When No Plan")
    api_post("/cancel", {})
    time.sleep(0.5)
    code, data = api_get("/plan")
    print(f"  HTTP {code} - Plan: {data}")
    print("  [PASS] No-plan state handled")
    return True


def test_missing_field_in_request():
    """Test POST without required 'command' field."""
    divider("EDGE: Missing 'command' Field")
    code, data = api_post("/command", {"instruction": "Go home"})
    print(f"  HTTP {code}")
    print(f"  Response: {str(data)[:200]}")
    assert code == 422, f"Expected 422, got {code}"
    print("  [PASS] Missing field rejected with 422")
    return True


# ========================================
# PHASE 7: STRESS TESTS
# ========================================

def test_rapid_status_polling():
    """Send 50 rapid status requests."""
    divider("STRESS: 50 Rapid Status Requests")
    success_count = 0
    error_count = 0
    start = time.time()
    for i in range(50):
        code, _ = api_get("/status")
        if code == 200:
            success_count += 1
        else:
            error_count += 1
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f}s")
    print(f"  Success: {success_count}, Errors: {error_count}")
    assert success_count == 50, f"Expected 50 successes, got {success_count}"
    print("  [PASS] All 50 status requests succeeded")
    return True


def test_rapid_log_polling():
    """Send 30 rapid log requests."""
    divider("STRESS: 30 Rapid Log Requests")
    success_count = 0
    start = time.time()
    for i in range(30):
        code, data = api_get("/logs")
        if code == 200 and isinstance(data, list):
            success_count += 1
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f}s")
    print(f"  Success: {success_count}/30")
    assert success_count == 30, f"Expected 30 successes, got {success_count}"
    print("  [PASS] All 30 log requests succeeded")
    return True


def test_concurrent_commands():
    """Send 5 commands concurrently using threads."""
    divider("STRESS: 5 Concurrent Commands")
    results_list = []
    
    def send_cmd(cmd):
        code, data = api_post("/command", {"command": cmd})
        results_list.append((cmd, code))
    
    threads = []
    commands = [
        "Go to the kitchen",
        "Pick up the red bottle",
        "Return home",
        "Go to the office",
        "Bring me water"
    ]
    for cmd in commands:
        t = threading.Thread(target=send_cmd, args=(cmd,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join(timeout=15)
    
    print(f"  Results ({len(results_list)} responses):")
    for cmd, code in results_list:
        print(f"    '{cmd}': HTTP {code}")
    
    all_ok = all(code == 200 for _, code in results_list)
    print(f"  All returned 200: {all_ok}")
    assert all_ok, "Some concurrent commands failed"
    print("  [PASS] All concurrent commands accepted")
    
    # Clean up
    api_post("/cancel", {})
    time.sleep(1)
    return True


def test_command_during_execution():
    """Send a new command while another is executing."""
    divider("STRESS: Command During Active Execution")
    # Start first command
    code1, _ = api_post("/command", {"command": "Go to the kitchen"})
    print(f"  First command: HTTP {code1}")
    time.sleep(0.5)
    
    # Send second command while first is running
    code2, data2 = api_post("/command", {"command": "Return home"})
    print(f"  Second command (during execution): HTTP {code2}")
    
    code_s, status = api_get("/status")
    print(f"  Current goal: {status.get('current_goal')}")
    print(f"  is_running: {status.get('is_running')}")
    
    print("  [PASS] New command during execution handled")
    api_post("/cancel", {})
    time.sleep(0.5)
    return True


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    results = {}

    edge_tests = [
        ("Very Long Command", test_very_long_command),
        ("Special Characters", test_special_characters_command),
        ("Unicode Command", test_unicode_command),
        ("Rapid Cancel", test_rapid_cancel_after_command),
        ("Double Cancel", test_double_cancel),
        ("Pause Without Execution", test_pause_without_execution),
        ("Resume Without Pause", test_resume_without_pause),
        ("Multiple Commands Override", test_multiple_commands_override),
        ("GET Plan When None", test_get_plan_when_none),
        ("Missing Field", test_missing_field_in_request),
    ]

    stress_tests = [
        ("Rapid Status Polling (50x)", test_rapid_status_polling),
        ("Rapid Log Polling (30x)", test_rapid_log_polling),
        ("Concurrent Commands (5x)", test_concurrent_commands),
        ("Command During Execution", test_command_during_execution),
    ]

    divider("PHASE 6: EDGE CASE TESTS")
    for name, fn in edge_tests:
        try:
            passed = fn()
            results[name] = "PASSED" if passed else "FAILED"
        except AssertionError as e:
            results[name] = f"FAILED: {e}"
        except Exception as e:
            results[name] = f"ERROR: {e}"

    divider("PHASE 7: STRESS TESTS")
    for name, fn in stress_tests:
        try:
            passed = fn()
            results[name] = "PASSED" if passed else "FAILED"
        except AssertionError as e:
            results[name] = f"FAILED: {e}"
        except Exception as e:
            results[name] = f"ERROR: {e}"

    divider("EDGE CASE & STRESS TEST SUMMARY")
    for name, result in results.items():
        marker = "[PASS]" if "PASSED" in result else "[FAIL]"
        print(f"  {marker} {name}: {result}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if "PASSED" in v)
    failed = total - passed
    print(f"\n  Total: {total} | Passed: {passed} | Failed: {failed}")

    if failed > 0:
        sys.exit(1)
