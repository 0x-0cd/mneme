"""
V0.3 Integration Test — Data Management + Plugin System + Multi-User

Runs against a REAL running Mneme server (not mocks).
Tests are FAIL-FAST: first failure stops the suite.
"""

import subprocess
import sys

import httpx

BASE = "http://localhost:8989"
PASS = 0
FAIL = 0


def req(method, path, body=None, params=None):
    """Make an HTTP request and return (status, data). Uses httpx for reliability."""
    url = f"{BASE}{path}"
    with httpx.Client(timeout=60.0) as client:
        if method == "GET":
            resp = client.get(url, params=params)
        elif method == "POST":
            resp = client.post(url, json=body, params=params)
        elif method == "PUT":
            resp = client.put(url, json=body, params=params)
        elif method == "DELETE":
            resp = client.delete(url, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        return resp.status_code, data


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")
        print(f"\n{'='*60}\nFAILED at test: {name}\n{'='*60}")
        sys.exit(1)


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ============================================================
# 0. CLEAR — start fresh
# ============================================================
section("0. CLEANUP — fresh start")
status, data = req("DELETE", "/v1/memories")
check("Clear all memories", status == 200)

# ============================================================
# 1. DATA MANAGEMENT — pagination + filtering
# ============================================================
section("1. DATA MANAGEMENT — pagination and filtering")

# Seed: 8 memories with various types/tags/weights
seeds = [
    {"content": "E=mc^2 is a physics formula", "type": "fact", "tags": ["science", "physics"], "weight": 1.0},
    {"content": "Python list comprehension syntax", "type": "fact", "tags": ["code", "python"], "weight": 0.9},
    {"content": "My favorite color is blue", "type": "preference", "tags": ["personal"], "weight": 0.5},
    {"content": "Buy groceries on Saturday", "type": "event", "tags": ["shopping", "weekly"], "weight": 0.8},
    {"content": "Albert Einstein developed relativity", "type": "fact", "tags": ["science", "history"], "weight": 0.7},
    {"content": "I dislike spicy food", "type": "preference", "tags": ["personal", "food"], "weight": 0.3},
    {"content": "Finish reading the book by Friday", "type": "event", "tags": ["reading"], "weight": 0.6},
    {"content": "Clean the kitchen after cooking", "type": "event", "tags": ["cleaning", "weekly"], "weight": 0.4},
]
memory_ids = []
for s in seeds:
    status, data = req("POST", "/v1/memories", body=s)
    check(f"Create: {s['content'][:30]}...", status == 201)
    memory_ids.append(data["id"])

# 1a. Pagination: limit=3, offset=0
status, data = req("GET", "/v1/memories", params={"limit": "3", "offset": "0"})
check("List with limit=3", status == 200 and len(data["results"]) == 3)
check("List total=8", data["total"] == 8)

# 1b. Pagination: offset=6, limit=3 (should get 2 remaining)
status, data = req("GET", "/v1/memories", params={"limit": "3", "offset": "6"})
check("List offset=6 limit=3", status == 200 and len(data["results"]) == 2)

# 1c. Filter by type
status, data = req("GET", "/v1/memories", params={"type": "event"})
check("Filter type=event", status == 200 and all(r["type"] == "event" for r in data["results"]))
check("Filter type=event count=3", data["total"] == 3)

# 1d. Filter by tags
status, data = req("GET", "/v1/memories", params={"tags": "science"})
check("Filter tags=science", status == 200 and data["total"] == 2)

# 1e. Filter by weight range
status, data = req("GET", "/v1/memories", params={"weight_min": "0.7", "weight_max": "1.0"})
check("Filter weight 0.7-1.0", status == 200 and data["total"] == 4)

# 1f. Sort by weight ascending
status, data = req("GET", "/v1/memories", params={"sort_by": "weight", "sort_order": "asc", "limit": "3"})
weights = [r["weight"] for r in data["results"]]
check("Sort weight asc", status == 200 and weights == sorted(weights))

# 1g. Sort by weight descending
status, data = req("GET", "/v1/memories", params={"sort_by": "weight", "sort_order": "desc", "limit": "3"})
weights = [r["weight"] for r in data["results"]]
check("Sort weight desc", status == 200 and weights == sorted(weights, reverse=True))

# 1h. Search with q param — semantic search returns multiple ranked results
status, data = req("GET", "/v1/memories", params={"q": "Einstein"})
check("Search q=Einstein returns 200", status == 200)
check("Search q=Einstein finds Einstein memory",
      any("Einstein" in r["content"] for r in data["results"]))
# First result should be the most relevant
check("First result is Einstein", "Einstein" in data["results"][0]["content"])

# ============================================================
# 2. DATA MANAGEMENT — batch operations + export/import + restore
# ============================================================
section("2. DATA MANAGEMENT — batch ops, export/import, restore")

# 2a. Batch delete by type (delete all 'preference' type)
status, data = req("POST", "/v1/memories/batch/delete", body={"type": "preference"})
check("Batch delete preferences", status == 200 and data["deleted"] == 2)

# Verify: 6 remaining (8 - 2)
status, data = req("GET", "/v1/memories")
check("6 memories after batch delete", status == 200 and data["total"] == 6)

# 2b. Restore one deleted memory
# Find the deleted ones first
status, data = req("GET", "/v1/memories", params={"include_deleted": "true"})
preference_ids = [r["id"] for r in data["results"] if r["type"] == "preference" and r["deleted_at"] is not None]
check("Found deleted preferences", len(preference_ids) >= 1)
restore_id = preference_ids[0]

status, data = req("POST", f"/v1/memories/{restore_id}/restore")
check("Restore memory", status == 200)

# Verify restored
status, data = req("GET", f"/v1/memories/{restore_id}")
check("Restored memory has no deleted_at", status == 200 and data["deleted_at"] is None)

# 2c. Batch update — mark all 'event' type items as 'conversation'
status, data = req("POST", "/v1/memories/batch/update", body={"type": "event", "updates": {"tags": ["plan", "urgent"]}})
check("Batch update event tags", status == 200 and data["updated"] >= 1)

# 2d. Export — save results
status, export_data = req("GET", "/v1/export")
check("Export returns memories", status == 200 and len(export_data) >= 1)
check("Export has content keys", "content" in export_data[0])
exported_count = len(export_data)

# 2e. Import — clear, then import back
status, _ = req("DELETE", "/v1/memories")
check("Clear for import test", status == 200)

status, data_empty = req("GET", "/v1/memories")
check("Empty after clear", status == 200 and data_empty["total"] == 0)

status, data = req("POST", "/v1/import", body=export_data)
check("Import memories", status == 200 and data["imported"] == exported_count)

status, data = req("GET", "/v1/memories", params={"include_deleted": "true"})
check("Imported count matches", status == 200 and data["total"] == exported_count)

# 2f. Detailed stats
status, data = req("GET", "/v1/stats/detailed")
check("Detailed stats endpoint", status == 200)
check("Stats has by_type", "by_type" in data)
check("Stats has total_weight", "total_weight" in data)
check("Stats has deleted_count", "deleted_count" in data)

print(f"\n  📊 Current stats: total={data.get('total')}, by_type={data.get('by_type')}")

# ============================================================
# 3. PLUGIN SYSTEM (CLI-only in V0.3)
# ============================================================
section("3. PLUGIN SYSTEM")

def cli(*args):
    """Run mneme CLI command and return stdout + stderr merged."""
    result = subprocess.run(
        [".venv/bin/mneme"] + list(args),
        capture_output=True, text=True, timeout=60,
        cwd="/home/qn/projects/ai-memory-system",
        env={**__import__("os").environ, "MNEME_DB_PATH": "memories.db"},
    )
    combined = (result.stdout + result.stderr).strip()
    return combined, result.returncode

# 3a. Plugin list
out, rc = cli("plugin", "list")
check("CLI plugin list runs", rc == 0)
# Builtin plugins are auto-loaded (logger + webhook)
check("Plugin list has entries", len(out) > 0)
print(f"  📋 Plugin list output:\n{out[:400]}")

# 3b. Trigger events by creating/searching via API
status, _ = req("POST", "/v1/memories", body={"content": "Test event for plugin", "type": "fact"})
check("Create memory (should trigger plugin events)", status == 201)

status, _ = req("GET", "/v1/memories", params={"q": "test"})
check("Search memories (should trigger plugin events)", status == 200)

# 3c. Verify LoggerPlugin fired by checking CLI stats or just confirm server alive
# (LoggerPlugin prints to stdout which goes to server logs - can't capture from here)
# But we can verify the auto-loading worked by checking plugin list
out, rc = cli("plugin", "list")
# Just confirm we don't get errors
check("Plugin list still works after events", rc == 0)

# 3d. Unload via CLI — note: each CLI invocation has its own plugin registry,
#     so unload is scoped to that process. Verify the command itself succeeds.
out, rc = cli("plugin", "unload", "logger")
check("CLI plugin unload logger", rc == 0 or "not loaded" in out)

# ============================================================
# 4. MULTI-USER
# ============================================================
section("4. MULTI-USER SUPPORT")

# 4a. Create memories for different users
for i, (content, uid) in enumerate([
    ("alice secret note", "alice"),
    ("alice shopping list", "alice"),
    ("bob project plan", "bob"),
    ("bob meeting notes", "bob"),
    ("charlie travel diary", "charlie"),
]):
    status, data = req("POST", "/v1/memories", body={"content": content, "user_id": uid})
    check(f"Create for {uid}: {content[:20]}...", status == 201)

# 4b. Alice sees only her memories
status, data = req("GET", "/v1/memories", params={"user_id": "alice"})
check("Alice sees 2 memories", status == 200 and data["total"] == 2)
check("All Alice results have user_id=alice", all(r["user_id"] == "alice" for r in data["results"]))

# 4c. Bob sees only his memories
status, data = req("GET", "/v1/memories", params={"user_id": "bob"})
check("Bob sees 2 memories", status == 200 and data["total"] == 2)
check("All Bob results have user_id=bob", all(r["user_id"] == "bob" for r in data["results"]))

# 4d. Charlie sees only his
status, data = req("GET", "/v1/memories", params={"user_id": "charlie"})
check("Charlie sees 1 memory", status == 200 and data["total"] == 1)
check("All Charlie results have user_id=charlie", all(r["user_id"] == "charlie" for r in data["results"]))

# 4e. No user_id sees all (including default "")
status, data = req("GET", "/v1/memories")
check("No user_id sees all memories", status == 200 and data["total"] >= 8)

# 4f. Search with user_id — verify isolation, not exact count
status, data = req("GET", "/v1/memories", params={"q": "project", "user_id": "alice"})
check("Alice search 'project' has 0 bob results", status == 200 and
      all("bob" not in r["content"].lower() for r in data["results"]))

status, data = req("GET", "/v1/memories", params={"q": "project", "user_id": "bob"})
check("Bob search 'project' has bob results", status == 200 and
      any("bob" in r["content"].lower() for r in data["results"]))
check("Bob search no alice content",
      all("alice" not in r["content"].lower() for r in data["results"]))

# 4g. GET /v1/users/{user_id}/memories
status, data = req("GET", "/v1/users/bob/memories")
check("Bob user endpoint returns memories", status == 200)
check("Bob user endpoint total=2", data["total"] == 2)

# 4h. Unknown user returns empty
status, data = req("GET", "/v1/users/unknown_user/memories")
check("Unknown user endpoint returns empty", status == 200 and data["total"] == 0 and len(data["results"]) == 0)

# 4i. Batch delete by user_id
status, data = req("POST", "/v1/memories/batch/delete", body={"user_id": "charlie"})
check("Batch delete charlie", status == 200 and data["deleted"] == 1)

status, data = req("GET", "/v1/memories", params={"user_id": "charlie"})
check("Charlie has 0 after batch delete", status == 200 and data["total"] == 0)

# 4j. Stats by user_id
status, data = req("GET", "/v1/stats/detailed", params={"user_id": "alice"})
check("Alice stats endpoint", status == 200)
check("Alice stats total=2", data.get("total") == 2)

status, data = req("GET", "/v1/stats", params={"user_id": "alice"})
check("Alice simple stats", status == 200)
check("Alice simple stats total=2", data.get("total") == 2)

# ============================================================
# 5. CLEANUP
# ============================================================
section("5. CLEANUP")
status, data = req("DELETE", "/v1/memories")
check("Final cleanup", status == 200)

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'='*60}")
print(f"  {'='*56}")
print(f"  RESULTS:  {PASS} passed,  {FAIL} failed")
print(f"  {'='*56}")
print(f"{'='*60}")

if FAIL > 0:
    sys.exit(1)
else:
    print("  ✅ ALL INTEGRATION TESTS PASSED")
    sys.exit(0)
