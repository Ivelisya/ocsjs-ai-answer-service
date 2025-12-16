import concurrent.futures
import requests
import time
import random

URL = "http://127.0.0.1:8000/api/search"

QUESTIONS = [
    {"title": "1+1等于几?", "type": "single", "options": "A. 1\nB. 2\nC. 3"},
    {"title": "中国的首都在哪里?", "type": "single", "options": "A. 上海\nB. 北京\nC. 广州"},
    {"title": "Python是什么?", "type": "completion", "options": ""},
    {"title": "地球是圆的吗?", "type": "judgement", "options": ""}
]

def send_request(idx):
    q = random.choice(QUESTIONS)
    start = time.time()
    try:
        response = requests.get(URL, params=q, timeout=10)
        code = response.status_code
        try:
             res_json = response.json()
             valid = res_json.get("code") == 1
        except:
             valid = False
        duration = time.time() - start
        return code, duration, valid
    except Exception as e:
        return 0, time.time() - start, False

def run_load_test(total_requests=50, concurrency=10):
    print(f"Starting load test: {total_requests} requests, concurrency {concurrency}")
    success_count = 0
    fail_count = 0
    latencies = []

    start_total = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, i) for i in range(total_requests)]
        
        for future in concurrent.futures.as_completed(futures):
            code, duration, valid = future.result()
            latencies.append(duration)
            if code == 200 and valid:
                success_count += 1
                print(".", end="", flush=True)
            else:
                fail_count += 1
                print("x", end="", flush=True)
    
    total_duration = time.time() - start_total
    print("\n\nLoad Test Results:")
    print(f"Total Requests: {total_requests}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total Time: {total_duration:.2f}s")
    print(f"QPS: {total_requests / total_duration:.2f}")
    if latencies:
        print(f"Avg Latency: {sum(latencies)/len(latencies):.4f}s")
        print(f"Max Latency: {max(latencies):.4f}s")
        print(f"Min Latency: {min(latencies):.4f}s")

if __name__ == "__main__":
    run_load_test()
