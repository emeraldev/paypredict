"""End-to-end flow test.

Exercises the full lifecycle against a running API server:
1. Login to get session token
2. Score a single collection via API
3. Score a bulk batch (sync, <=50)
4. Report outcomes for scored collections
5. Check analytics updated
6. Upload a CSV backtest
7. Verify backtest results
8. Check alerts
9. List scores via dashboard endpoint

Usage: python scripts/test_flow.py [base_url]
Default base_url: http://localhost:8001
"""

import sys
import json
import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
API_KEY = None  # Set after login from seed data
TOKEN = None

passed = 0
failed = 0


def step(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    icon = "✓" if condition else "✗"
    print(f"  {icon} {label}: {status}", end="")
    if detail and not condition:
        print(f"  ({detail})", end="")
    print()
    if condition:
        passed += 1
    else:
        failed += 1


def main():
    global API_KEY, TOKEN
    client = httpx.Client(base_url=BASE_URL, timeout=30)

    # ---- Step 1: Login ----
    step("1. Login")
    r = client.post("/v1/auth/login", json={
        "email": "admin@demo-sa.paypredict.dev",
        "password": "admin123",
    })
    check("Login status 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        TOKEN = data["token"]
        check("Token received", bool(TOKEN))
        check("User has tenant", "tenant" in data["user"])
        print(f"  Tenant: {data['user']['tenant']['name']}")

    auth = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

    # Get API key from config
    r = client.get("/v1/config/api-keys", headers=auth)
    if r.status_code == 200 and r.json()["items"]:
        # Use the first active key's info — but we need the raw key from seed
        # For this test, we'll use the seed's printed API key
        pass

    # ---- Step 2: Score single collection ----
    step("2. Score single collection")
    # We need an API key. Get it from the seed output or use the health endpoint
    # to verify the server is up, then try scoring with the seed key.
    r = client.get("/v1/health")
    check("Health endpoint", r.status_code == 200)

    # Try to find a working API key by listing keys
    # Since we can't get the raw key from the API, we'll create a new one
    r = client.post("/v1/config/api-keys", headers=auth, json={"label": "E2E Test Key"})
    check("Create API key", r.status_code == 201, f"got {r.status_code}")
    if r.status_code == 201:
        API_KEY = r.json()["key"]
        check("Raw key received", API_KEY.startswith("pk_live_"))

    api_auth = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

    score_payload = {
        "external_customer_id": "e2e_cust_001",
        "external_collection_id": "e2e_col_001",
        "collection_amount": 1500.00,
        "collection_currency": "ZAR",
        "collection_due_date": "2026-05-15",
        "collection_method": "CARD",
        "customer_data": {
            "total_payments": 10,
            "successful_payments": 7,
            "card_type": "debit",
            "instalment_number": 3,
            "total_instalments": 6,
        },
    }
    r = client.post("/v1/score", headers=api_auth, json=score_payload)
    check("Score status 200", r.status_code == 200, f"got {r.status_code}")
    score_id = None
    if r.status_code == 200:
        data = r.json()
        score_id = data["score_id"]
        check("Score in 0-1 range", 0 <= data["score"] <= 1, f"score={data['score']}")
        check("Risk level valid", data["risk_level"] in ("LOW", "MEDIUM", "HIGH"))
        check("Factors returned", len(data["factors"]) > 0, f"count={len(data['factors'])}")
        print(f"  Score: {data['score']:.4f} ({data['risk_level']})")

    # ---- Step 3: Bulk score ----
    step("3. Bulk score (sync, 5 items)")
    bulk_items = []
    for i in range(5):
        item = score_payload.copy()
        item["external_customer_id"] = f"e2e_bulk_{i:03d}"
        item["external_collection_id"] = f"e2e_bcol_{i:03d}"
        item["collection_amount"] = 1000 + i * 200
        bulk_items.append(item)

    r = client.post("/v1/score/bulk", headers=api_auth, json={"collections": bulk_items})
    check("Bulk score status 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Status completed", data["status"] == "completed")
        check("All items scored", data["total_items"] == 5)
        check("Summary present", "summary" in data)

    # ---- Step 4: Report outcomes ----
    step("4. Report outcomes")
    if score_id:
        r = client.post("/v1/outcomes", headers=api_auth, json={
            "score_id": score_id,
            "external_collection_id": "e2e_col_001",
            "outcome": "FAILED",
            "failure_reason": "insufficient_funds",
            "attempted_at": "2026-05-15T08:00:00Z",
        })
        check("Outcome status 201", r.status_code == 201, f"got {r.status_code}")
        if r.status_code == 201:
            check("Linked to score", r.json()["linked_score_id"] == score_id)

    # ---- Step 5: Check analytics ----
    step("5. Analytics")
    r = client.get("/v1/analytics/summary?period=30d", headers=auth)
    check("Analytics status 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Total scored > 0", data["total_scored"] > 0, f"total={data['total_scored']}")
        check("Risk distribution present", "risk_distribution" in data)
        print(f"  Total scored: {data['total_scored']}, Rate: {data['collection_rate']:.1%}")

    # ---- Step 6: Backtest CSV upload ----
    step("6. Backtest CSV upload")
    csv_content = (
        "external_customer_id,external_collection_id,collection_amount,"
        "collection_currency,collection_date,collection_method,"
        "instalment_number,total_instalments,total_payments,"
        "successful_payments,card_type,card_expiry,actual_outcome,failure_reason\n"
        "bt_001,bt_col_001,800,ZAR,2025-10-15,CARD,2,6,8,5,debit,2026-09-01,FAILED,insufficient_funds\n"
        "bt_002,bt_col_002,500,ZAR,2025-10-20,CARD,1,3,4,4,credit,,SUCCESS,\n"
        "bt_003,bt_col_003,1200,ZAR,2025-11-01,DEBIT_ORDER,3,6,10,7,,,FAILED,do_not_honour\n"
        "bt_004,bt_col_004,350,ZAR,2025-11-05,CARD,1,4,2,2,debit,2027-01-01,SUCCESS,\n"
        "bt_005,bt_col_005,950,ZAR,2025-11-10,CARD,4,6,12,4,debit,2026-06-01,FAILED,general_decline\n"
    )
    r = client.post(
        "/v1/backtest/upload",
        headers=auth,
        files={"file": ("e2e_test.csv", csv_content.encode(), "text/csv")},
    )
    check("Backtest upload status 201", r.status_code == 201, f"got {r.status_code}")
    backtest_id = None
    if r.status_code == 201:
        data = r.json()
        backtest_id = data.get("backtest_id")
        check("Backtest completed", data["status"] == "COMPLETED")
        check("5 collections backtested", data["total_collections"] == 5)
        if data.get("summary"):
            check("Accuracy computed", 0 <= data["summary"]["overall_accuracy"] <= 1)
            print(f"  Accuracy: {data['summary']['overall_accuracy']:.1%}")

    # ---- Step 7: Verify backtest retrieval ----
    step("7. Verify backtest retrieval")
    if backtest_id:
        r = client.get(f"/v1/backtest/{backtest_id}", headers=auth)
        check("Get backtest status 200", r.status_code == 200)
        if r.status_code == 200:
            check("Same ID", r.json()["backtest_id"] == backtest_id)

    r = client.get("/v1/backtests", headers=auth)
    check("List backtests", r.status_code == 200)
    if r.status_code == 200:
        check("At least 1 backtest", len(r.json()["items"]) >= 1)

    # ---- Step 8: Check alerts ----
    step("8. Alerts")
    r = client.get("/v1/alerts", headers=auth)
    check("Alerts status 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Alerts list present", "items" in data)
        check("Unread count present", "unread_count" in data)
        print(f"  {len(data['items'])} alerts, {data['unread_count']} unread")

    # ---- Step 9: List scores (dashboard) ----
    step("9. List scores (dashboard endpoint)")
    r = client.get("/v1/scores?page=1&page_size=10", headers=auth)
    check("Scores list status 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Items returned", len(data["items"]) > 0)
        check("Pagination present", "pagination" in data)
        check("Summary present", "summary" in data)
        print(f"  {data['pagination']['total_items']} total scores")

    # ---- Summary ----
    print(f"\n{'='*60}")
    total = passed + failed
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")

    client.close()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
