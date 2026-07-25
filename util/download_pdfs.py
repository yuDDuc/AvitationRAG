import requests
import os
from urllib.parse import urlparse

def download_pdfs_from_urls(url_file_path: str, output_folder: str):
    """
    Tải xuống các file PDF từ danh sách URL trong một file text.
    Mỗi URL trên một dòng.
    """
    if not os.path.exists(url_file_path):
        print(f"Lỗi: File URL không tồn tại tại {url_file_path}")
        return

    os.makedirs(output_folder, exist_ok=True)

    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Tìm thấy {len(urls)} URL. Bắt đầu tải xuống...")

    for i, url in enumerate(urls):
        try:
            # Lấy tên file từ URL
            a = urlparse(url)
            filename = os.path.basename(a.path)
            if not filename.endswith('.pdf'):
                filename = f"document_{i+1}.pdf" # Tên mặc định nếu không có trong URL

            file_save_path = os.path.join(output_folder, filename)
            
            print(f"Đang tải: {url} -> {filename}")
            response = requests.get(url, stream=True)
            response.raise_for_status() # Báo lỗi nếu status code không phải 200

            with open(file_save_path, 'wb') as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)
            print(f"✅ Tải xuống thành công: {filename}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi khi tải xuống {url}: {e}")
        except Exception as e:
            print(f"❌ Lỗi không xác định khi xử lý {url}: {e}")

if __name__ == "__main__":
    # Thay đổi đường dẫn đến file test_pdf.txt của bạn
    # Ví dụ: nếu file test_pdf.txt nằm trong thư mục gốc của project ojt
    # url_list_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_pdf.txt")
    
    # Giả sử test_pdf.txt nằm cùng cấp với thư mục project ojt
    current_dir = os.getcwd()
    url_list_file = os.path.join(current_dir, "test_pdf.txt") 
    
    output_folder_path = os.path.join(current_dir, "project ojt", "original data")
    
    print(f"Tìm file URL tại: {url_list_file}")
    download_pdfs_from_urls(url_list_file, output_folder_path)
