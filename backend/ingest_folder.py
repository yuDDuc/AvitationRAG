import os
import requests
import argparse

def ingest_folder(folder_path, subject, api_url):
    """
    Script nạp toàn bộ file trong thư mục vào hệ thống RAG qua API.
    """
    if not os.path.exists(folder_path):
        print(f"Lỗi: Thư mục {folder_path} không tồn tại.")
        return

    # Lấy danh sách các file hỗ trợ
    valid_extensions = ('.pdf', '.docx', '.pptx')
    files_to_upload = [
        f for f in os.listdir(folder_path) 
        if f.lower().endswith(valid_extensions)
    ]

    if not files_to_upload:
        print(f"Không tìm thấy file hợp lệ (.pdf, .docx, .pptx) trong {folder_path}")
        return

    print(f"Tìm thấy {len(files_to_upload)} tài liệu. Bắt đầu nạp vào môn học: {subject}...")

    # Chuẩn bị dữ liệu cho multi-file upload
    upload_url = f"{api_url}/api/v1/documents/upload-batch"
    
    # Mở các file
    files = []
    file_handles = []
    for filename in files_to_upload:
        file_path = os.path.join(folder_path, filename)
        f = open(file_path, 'rb')
        file_handles.append(f)
        files.append(('files', (filename, f)))

    try:
        response = requests.post(
            upload_url, 
            data={'subject': subject}, 
            files=files
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\nKết quả:")
            print(f"Thông báo: {result['message']}")
            for detail in result['details']:
                status_icon = "✅" if detail['status'] == "success" else "❌"
                chunks_info = f"({detail.get('chunks', 0)} chunks)" if detail['status'] == "success" else f"Lỗi: {detail.get('message')}"
                print(f"{status_icon} {detail['file']} {chunks_info}")
        else:
            print(f"Lỗi API (Status {response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"Lỗi kết nối đến Server: {str(e)}")
    finally:
        # Đóng tất cả file handles
        for f in file_handles:
            f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nạp thư mục tài liệu vào Aviation RAG")
    parser.add_argument("--folder", type=str, required=True, help="Đường dẫn đến thư mục chứa tài liệu")
    parser.add_argument("--subject", type=str, required=True, help="Tên môn học")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000", help="URL của Backend API (mặc định: http://127.0.0.1:8000)")

    args = parser.parse_args()
    ingest_folder(args.folder, args.subject, args.url)
