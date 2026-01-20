import os
from llama_index.core import SimpleDirectoryReader
from app.core.config import settings
def load_documents_from_folder():
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR)
        print(f"Đã tạo thư mục: {settings.UPLOAD_DIR}")
        return []
    
    print(f"Đang quét file trong: {settings.UPLOAD_DIR}")

    required_exts = [".pdf", ".docx", ".doc", ".txt", ".text"]

    try:
        reader = SimpleDirectoryReader(
            input_dir=settings.UPLOAD_DIR,
            required_exts=required_exts,
            recursive=True,
            filename_as_id=True
        )
        
        documents = reader.load_data()
        print(f"Đã đọc được {len(documents)} tài liệu.")
        return documents
        
    except Exception as e:
        print(f"Lỗi khi đọc file: {e}")
        return []