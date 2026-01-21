import os
import io
from llama_index.core import SimpleDirectoryReader, Document
from app.core.config import settings
import pypdf
import docx


# --- CÁCH 1: Dùng cho DEV (Quét folder) ---
def load_documents_from_folder():
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR)
        print(f"Đã tạo thư mục: {settings.UPLOAD_DIR}")
        return []

    print(f"Đang quét file trong: {settings.UPLOAD_DIR}")

    # Định nghĩa các đuôi file hỗ trợ
    required_exts = [".pdf", ".docx", ".doc", ".txt"]

    try:
        reader = SimpleDirectoryReader(
            input_dir=settings.UPLOAD_DIR,
            required_exts=required_exts,
            recursive=True,
            filename_as_id=True,
        )

        documents = reader.load_data()
        print(f"Đã đọc được {len(documents)} tài liệu từ ổ cứng.")
        return documents

    except Exception as e:
        print(f"Lỗi khi đọc file từ folder: {e}")
        return []


# --- CÁCH 2: Dùng cho PRODUCTION/API (Xử lý trên RAM) ---
def process_file_in_memory(filename: str, file_bytes: bytes):
    """
    Xử lý file từ byte raw (không cần lưu xuống ổ cứng).
    Hỗ trợ: PDF, DOCX, TXT
    """
    text_content = ""
    file_stream = io.BytesIO(file_bytes)

    try:
        # 1. Xử lý PDF
        if filename.lower().endswith(".pdf"):
            pdf_reader = pypdf.PdfReader(file_stream)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"

        # 2. Xử lý DOCX
        elif filename.lower().endswith(".docx"):
            doc = docx.Document(file_stream)
            for para in doc.paragraphs:
                text_content += para.text + "\n"

        # 3. Xử lý TXT
        elif filename.lower().endswith(".txt"):
            text_content = file_stream.read().decode("utf-8")

        else:
            print(f"Định dạng file chưa hỗ trợ: {filename}")
            return []

    except Exception as e:
        print(f"Lỗi đọc file {filename}: {e}")
        return []

    # Nếu trích xuất được chữ thì trả về Document
    if text_content.strip():
        # metadata giúp AI biết nội dung này từ file nào
        return [Document(text=text_content, metadata={"filename": filename})]

    return []
