import sys
import os
from sqlalchemy import create_engine, text

# Hack đường dẫn để import được app
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from app.core.config import settings

def debug_database():
    print("--- BẮT ĐẦU DEBUG DATABASE ---")
    
    # 1. Tạo kết nối (Connection String)
    # Lấy thông tin từ file config của ông
    db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    print(f"1. Đang kết nối tới: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT} DB: {settings.POSTGRES_DB}")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("   ✅ Kết nối thành công!")

            # 2. Liệt kê tất cả các bảng hiện có trong DB
            print("\n2. Kiểm tra danh sách bảng (Tables):")
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            
            if not tables:
                print("   ❌ CẢNH BÁO: Không tìm thấy bảng nào trong schema 'public'!")
            else:
                for t in tables:
                    print(f"   - {t}")

            # 3. Kiểm tra dữ liệu trong bảng 'embeddings' (hoặc tên bảng ông nghi ngờ)
            target_table = "embeddings" # <--- Tên bảng ông định dùng
            
            if target_table in tables:
                count_query = text(f"SELECT count(*) FROM {target_table}")
                count = conn.execute(count_query).scalar()
                print(f"\n3. Soi bảng '{target_table}':")
                print(f"   -> Tổng số dòng: {count}")
                
                if count > 0:
                    # Soi thử 1 dòng xem vector có null không
                    sample = conn.execute(text(f"SELECT id, content, embedding FROM {target_table} LIMIT 1")).first()
                    print(f"   -> Sample Content: {sample[1][:50]}...")
                    if sample[2] is None:
                        print("   ❌ CẢNH BÁO: Cột vector (embedding) đang bị NULL! (Lỗi lúc ingest)")
                    else:
                        print(f"   ✅ Vector OK. Độ dài vector: {len(sample[2]) if hasattr(sample[2], '__len__') else 'Unknown'}")
                        # all-MiniLM-L6-v2 phải là 384 dimensions
                else:
                    print("   ❌ Bảng có tồn tại nhưng RỖNG (0 dòng). Ông chưa Ingest thành công!")
            
            # 4. Kiểm tra xem có bảng 'data_embeddings' (tên mặc định của LlamaIndex) không
            elif "data_embeddings" in tables:
                print(f"\n❌ Ông đang lưu nhầm vào bảng 'data_embeddings' rồi, trong khi code lại tìm 'embeddings'!")
            
            else:
                print(f"\n❌ Không tìm thấy bảng '{target_table}' đâu cả. Ông đã chạy Ingest chưa?")

    except Exception as e:
        print(f"\n❌ Lỗi kết nối chết người: {e}")

if __name__ == "__main__":
    debug_database()