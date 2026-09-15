"""Test script for OncoVision AI Chat & Summary endpoints."""
import httpx
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"


def pp(label: str, r: httpx.Response):
    """Pretty print response."""
    print(f"\n{'='*60}")
    print(f"📌 {label}")
    print(f"   Status: {r.status_code}")
    try:
        data = r.json()
        print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}")
    except Exception:
        print(f"   Body: {r.text[:500]}")
    print(f"{'='*60}")
    return r


def main():
    client = httpx.Client(base_url=BASE, timeout=60.0)

    # Step 1: Register a test user
    print("\n🔹 Step 1: Registering test user...")
    r = client.post(f"{API}/auth/register", json={
        "email": "testllm@oncovision.ai",
        "password": "Test@12345",
        "confirm_password": "Test@12345",
        "full_name": "Test LLM User"
    })
    pp("Register", r)

    # Step 2: Login to get JWT token
    print("\n🔹 Step 2: Logging in...")
    r = client.post(f"{API}/auth/login", json={
        "email": "testllm@oncovision.ai",
        "password": "Test@12345"
    })
    pp("Login", r)
    login_data = r.json()
    
    if not login_data.get("success"):
        print("❌ Login failed! Cannot proceed.")
        sys.exit(1)
    
    token = login_data["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Got token: {token[:20]}...")

    # Step 3: Test Knowledge Chat (RAG)
    print("\n🔹 Step 3: Testing Knowledge Chat (POST /chat/knowledge)...")
    r = client.post(f"{API}/chat/knowledge", json={
        "message": "What is lung adenocarcinoma? Tell me briefly.",
        "language": "en"
    }, headers=headers)
    pp("Knowledge Chat (English)", r)

    # Step 4: Test Knowledge Chat in Bangla
    print("\n🔹 Step 4: Testing Knowledge Chat in Bangla...")
    r = client.post(f"{API}/chat/knowledge", json={
        "message": "কোলন ক্যান্সার কি? সংক্ষেপে বলুন।",
        "language": "bn"
    }, headers=headers)
    pp("Knowledge Chat (Bangla)", r)

    # Step 5: Get prediction history to find a prediction_id
    print("\n🔹 Step 5: Getting prediction history for prediction chat test...")
    r = client.get(f"{API}/predictions/history", headers=headers)
    pp("Prediction History", r)
    
    history_data = r.json()
    prediction_id = None
    if history_data.get("success") and history_data.get("data"):
        records = history_data["data"]
        if isinstance(records, list) and len(records) > 0:
            prediction_id = records[0].get("id")
        elif isinstance(records, dict) and records.get("records"):
            prediction_id = records["records"][0].get("id")
    
    if prediction_id:
        # Step 6: Test Prediction Chat
        print(f"\n🔹 Step 6: Testing Prediction Chat (prediction_id={prediction_id})...")
        r = client.post(f"{API}/chat/prediction/{prediction_id}", json={
            "message": "What does this prediction mean? Is it serious?",
            "language": "en"
        }, headers=headers)
        pp("Prediction Chat", r)

        # Step 7: Test Prediction Summary
        print(f"\n🔹 Step 7: Testing Prediction Summary...")
        r = client.post(f"{API}/predictions/{prediction_id}/summary", json={
            "language": "en"
        }, headers=headers)
        pp("Prediction Summary", r)

        # Step 8: Test Prediction Summary in Bangla
        print(f"\n🔹 Step 8: Testing Prediction Summary (Bangla)...")
        r = client.post(f"{API}/predictions/{prediction_id}/summary", json={
            "language": "bn"
        }, headers=headers)
        pp("Prediction Summary (Bangla)", r)
    else:
        print("\n⚠️  No predictions found — skipping prediction chat & summary tests.")
        print("   (Upload a histopathology image first to create a prediction)")

    # Step 9: Test Chat History (using conversation_id from knowledge chat if available)
    print("\n🔹 Step 9: Testing chat history retrieval...")
    try:
        knowledge_resp = client.post(f"{API}/chat/knowledge", json={
            "message": "What is cancer staging?",
            "language": "en"
        }, headers=headers)
        kr = knowledge_resp.json()
        if kr.get("success") and kr.get("data", {}).get("conversation_id"):
            conv_id = kr["data"]["conversation_id"]
            r = client.get(f"{API}/chat/history/{conv_id}", headers=headers)
            pp("Chat History", r)
    except Exception as e:
        print(f"   ⚠️ Chat history test skipped: {e}")

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()
