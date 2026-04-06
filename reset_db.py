import sys
import os
import logging
from sqlalchemy import text
from app.core.db.rag_database import rag_engine, RagBase, setup_database
from app.models import Document, Embedding, RagConfig, Collection

# Add current directory to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    try:
        print("Đang xóa toàn bộ bảng dữ liệu cũ...")
        RagBase.metadata.drop_all(bind=rag_engine)
        print("Đã xóa xong.")
        
        print("Đang tạo lại các bảng và extension mới...")
        with rag_engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
            
        RagBase.metadata.create_all(bind=rag_engine)
        
        setup_database()
        print("Đã khởi tạo database sạch thành công (1024 dim + fts_vector).")
        
    except Exception as e:
        print(f"Lỗi khi reset database: {e}")

if __name__ == "__main__":
    confirm = input("Bạn có chắc chắn muốn XÓA HẾT dữ liệu cũ và tạo lại database không? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Đã hủy bỏ.")
