import requests
import json
import os
import argparse

def generate_and_save_mock_questions(
    subject: str, 
    num_questions: int, 
    output_file: str, 
    api_base_url: str = "http://127.0.0.1:8000/api/v1"
):
    """
    Kết nối API để sinh câu hỏi trắc nghiệm và lưu vào file text.
    """
    quiz_api_url = f"{api_base_url}/quiz/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "subject": subject,
        "num_questions": num_questions
    }

    print(f"Đang kết nối API: {quiz_api_url} để sinh {num_questions} câu hỏi cho môn {subject}...")

    try:
        response = requests.post(quiz_api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Báo lỗi nếu HTTP status code là lỗi

        result = response.json()
        quiz_json_str = result.get("quiz", "[]") # Lấy chuỗi JSON của quiz

        # Parse chuỗi JSON thành đối tượng Python
        quiz_data = json.loads(quiz_json_str)

        if not quiz_data:
            print("API không trả về câu hỏi nào.")
            return

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"--- MOCK TEST CHO MÔN: {subject.upper()} ({num_questions} CÂU) ---

")
            for i, q in enumerate(quiz_data):
                f.write(f"Câu {i+1}: {q.get('question', 'N/A')}
")
                options = q.get('options', {})
                for opt_key, opt_val in options.items():
                    f.write(f"  {opt_key}. {opt_val}
")
                f.write(f"Đáp án: {q.get('answer', 'N/A')}
")
                f.write(f"Giải thích: {q.get('explanation', 'N/A')}
")
                f.write("-" * 50 + "

")
        
        print(f"✅ Đã sinh và lưu {len(quiz_data)} câu hỏi vào file: {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối API hoặc server: {e}")
        if response is not None:
            print(f"API Response: {response.text}")
    except json.JSONDecodeError as e:
        print(f"❌ Lỗi khi phân tích JSON từ API: {e}")
        print(f"Raw API Response: {quiz_json_str}")
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh câu hỏi trắc nghiệm mock test từ API.")
    parser.add_argument("--subject", type=str, required=True, help="Tên môn học để sinh câu hỏi.")
    parser.add_argument("--count", type=int, default=10, help="Số lượng câu hỏi muốn sinh.")
    parser.add_argument("--output", type=str, default="mock_questions.txt", help="Tên file để lưu câu hỏi.")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000/api/v1", help="URL base của Backend API.")

    args = parser.parse_args()
    
    # Đảm bảo output file nằm trong thư mục gốc của project ojt
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.output)
    
    generate_and_save_mock_questions(
        subject=args.subject,
        num_questions=args.count,
        output_file=output_path,
        api_base_url=args.url
    )
