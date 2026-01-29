import httpx
import json
import time

# 配置
API_KEY = "2df32239-0ce0-4a05-92d2-a0d6aafe857d"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "ep-m-20260117202637-5v5nj"

# 测试请求
url = f"{BASE_URL}/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "hi"}],
    "temperature": 0.7,
    "stream": False
}

print(f"Testing API: {url}")
print(f"Model: {MODEL}")
print(f"API Key: {API_KEY[:20]}...")
print("\nSending request...")

start_time = time.time()

try:
    # force disable proxy with trust_env=False
    with httpx.Client(timeout=30.0, trust_env=False) as client:
        response = client.post(url, json=payload, headers=headers)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nStatus: {response.status_code}")
        print(f"Time Taken: {duration:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            print(f"Response: {content}")
        else:
            print(f"Error: {response.text}")
            
except httpx.TimeoutException:
    print("Timeout: API response timed out")
except Exception as e:
    print(f"Error: {e}")
