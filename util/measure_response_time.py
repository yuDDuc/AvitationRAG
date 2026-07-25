import urllib.request
import urllib.error
import json
import uuid
import time
import datetime
import os

API_URL = "http://localhost:8000/api/v1/chat/completions"

QUESTIONS = [
    "Xin chào",
    "Thế nào là an toàn bay?",
    "Phi công chỉ huy (PIC) là ai?",
    "Hoạt động nào KHÔNG được liệt kê là một thực hành an toàn vận hành?",
    "ATC là gì?"
]

def measure_time(message: str):
    req_data = {
        "message": message,
        "subject": "",
        "user_id": "test_perf_123",
        "session_id": str(uuid.uuid4())
    }
    
    req = urllib.request.Request(
        API_URL, 
        data=json.dumps(req_data).encode("utf-8"), 
        headers={"Content-Type": "application/json"}
    )
    
    start_time = time.time()
    first_token_time = None
    full_response = ""
    
    try:
        with urllib.request.urlopen(req) as response:
            for line in response:
                if first_token_time is None:
                    first_token_time = time.time()
                
                decoded_line = line.decode("utf-8").strip()
                if decoded_line.startswith("data: "):
                    data_content = decoded_line[6:]
                    if data_content.startswith("[{") or data_content.startswith("[]") or "event: sources" in decoded_line:
                        continue
                    full_response += data_content.replace("\\n", "\n")
    except Exception as e:
        return {"question": message, "error": str(e)}
        
    end_time = time.time()
    
    ttft = (first_token_time - start_time) if first_token_time else 0
    total_time = end_time - start_time
    
    return {
        "question": message,
        "time_to_first_token_sec": round(ttft, 4),
        "total_time_sec": round(total_time, 4),
        "response_length": len(full_response)
    }

def main():
    print("==================================================")
    print("⏱️  RESPONSE TIME MEASUREMENT UTILITY")
    print("==================================================\n")
    
    results = []
    for q in QUESTIONS:
        print(f"Testing: \"{q}\"")
        res = measure_time(q)
        results.append(res)
        
        if "error" in res:
            print(f"  [ERROR] {res['error']}")
        else:
            print(f"  -> TTFT (Time to First Token): {res['time_to_first_token_sec']}s")
            print(f"  -> Total Time                : {res['total_time_sec']}s")
        print("-" * 50)
        time.sleep(1) # cool down
        
    output_file = os.path.join(os.path.dirname(__file__), "response_times.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.datetime.now().isoformat(),
            "measurements": results
        }, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Results saved to {output_file}")

if __name__ == "__main__":
    main()
