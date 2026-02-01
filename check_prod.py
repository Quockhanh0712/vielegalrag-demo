import requests
import sys
import json
import time

# CONFIG
BASE_URL = "https://vielegalrag-demo.onrender.com"  # Change to localhost:8080 for local
# BASE_URL = "http://localhost:8080"

def print_result(name, success, details=""):
    icon = "✅" if success else "❌"
    print(f"{icon} [{name}]: {details}")
    if not success:
        print(f"   >>> ACTION REQUIRED: {details}")

def test_health():
    print(f"\n1. Testing Health ({BASE_URL}/api/status)...")
    try:
        res = requests.get(f"{BASE_URL}/api/status")
        if res.status_code != 200:
            print_result("Health Check", False, f"Status Code {res.status_code}")
            return False
        
        data = res.json()
        
        # Check Components
        qdrant = data.get("qdrant", {})
        print_result("Qdrant Connection", qdrant.get("status") in ["connected", "warning"], qdrant.get("message"))
        
        llm = data.get("ollama", {}) # Note: API key is 'ollama' but maps to generic LLM
        print_result("LLM Provider", llm.get("status") == "available", llm.get("message"))
        
        db = data.get("database", {})
        print_result("SQLite DB", db.get("status") == "connected", db.get("message"))
        
        return True
    except Exception as e:
        print_result("Health Check", False, f"Connection Failed: {str(e)}")
        return False

def test_search():
    print(f"\n2. Testing Search Pipeline (Embedding -> Qdrant)...")
    query = "Hành vi trộm cắp tài sản bị phạt thế nào?"
    try:
        res = requests.post(f"{BASE_URL}/api/search", json={
            "query": query,
            "top_k": 3,
            "mode": "legal"
        })
        
        if res.status_code != 200:
            print_result("Search API", False, f"Status {res.status_code} - {res.text}")
            return

        results = res.json().get("results", [])
        if not results:
            print_result("RAG Retrieval", False, "No results found. (Is Qdrant collection empty?)")
        else:
            top_doc = results[0]
            print_result("RAG Retrieval", True, f"Found {len(results)} docs. Top: {top_doc.get('metadata', {}).get('dieu', 'Unknown')}")
            
    except Exception as e:
        print_result("Search API", False, str(e))

def test_chat():
    print(f"\n3. Testing LLM Generation (FPT Cloud)...")
    try:
        # 1. Check active provider
        res = requests.get(f"{BASE_URL}/api/llm/active")
        provider = res.json()
        print(f"   Active Provider: {provider.get('provider')} ({provider.get('model')})")
        
        # 2. Test Chat
        start = time.time()
        res = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Xin chào, bạn là ai?"}],
            "stream": False # Disable stream for simple test
        })
        latency = time.time() - start
        
        if res.status_code == 200:
            try:
                # Handle potential stream response or json
                data = res.json()
                answer = data.get("answer", "")
                print_result("LLM Generation", True, f"Response ({latency:.2f}s): {answer[:50]}...")
            except:
                print_result("LLM Generation", True, f"Response received (Stream/Text) in {latency:.2f}s")
        else:
            print_result("LLM Generation", False, f"Status {res.status_code} - {res.text}")
            
    except Exception as e:
         print_result("LLM Generation", False, str(e))

if __name__ == "__main__":
    print(f"=== SYSTEM DIAGNOSTIC TOOL ===")
    print(f"Target: {BASE_URL}")
    
    if test_health():
        test_search()
        test_chat()
    
    print("\n=== TEST COMPLETE ===")
