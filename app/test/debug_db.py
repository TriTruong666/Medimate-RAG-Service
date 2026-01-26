import sys
import os
import json
from sqlalchemy import create_engine, text

# Setup đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from app.core.config import settings
from app.services.model_loader import get_embed_model

def debug_raw_sql():
    print("🚀 BẮT ĐẦU DEBUG RAW SQL...")
    
    # 1. Tạo vector mẫu từ Model thật
    print("1. Đang tạo embedding mẫu cho từ khóa 'HTTPS'...")
    embed_model = get_embed_model()
    query_vector = embed_model.get_text_embedding("Giai đoạn 1")
    
    # Convert vector thành chuỗi format của Postgres: '[0.1, 0.2, ...]'
    vector_str = str(query_vector)
    
    # 2. Kết nối DB
    db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("\n2. KIỂM TRA KIỂU DỮ LIỆU CỘT EMBEDDING...")
        # Check xem cột embedding là kiểu 'vector' hay 'double precision[]'
        type_check = conn.execute(text("""
            SELECT udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'embeddings' AND column_name = 'embedding'
        """)).scalar()
        
        print(f"👉 Kiểu dữ liệu trong DB là: '{type_check}'")
        
        if type_check != 'vector':
            print("❌ LỖI CHÍ MẠNG: Cột embedding KHÔNG PHẢI kiểu vector!")
            print("   -> Nó đang là mảng thường. PGVector không search được trên cái này.")
            print("   -> Giải pháp: Phải Drop bảng và chạy lại từ đầu với extension vector được bật.")
            return

        print("\n3. THỰC HIỆN SEARCH BẰNG SQL THUẦN (Toán tử <=>)")
        try:
            # Câu lệnh SQL tìm kiếm vector gần nhất (Cosine Distance)
            # Lấy 3 thằng gần nhất
            sql = text(f"""
                SELECT text, (embedding <=> '{vector_str}') as distance
                FROM embeddings
                WHERE embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT 3;
            """)
            
            results = conn.execute(sql).fetchall()
            
            if not results:
                print("❌ KẾT QUẢ: 0 dòng. (Vô lý vì bảng có dữ liệu!)")
            else:
                print(f"✅ KẾT QUẢ: Tìm thấy {len(results)} dòng tương đồng!")
                for idx, row in enumerate(results):
                    print(f"   Top {idx+1}: Distance = {row[1]:.4f}")
                    print(f"   Content: {row[0][:100]}...")
                    
                print("\n✅ KẾT LUẬN: Database và Vector NGON LÀNH.")
                print("   -> Lỗi nằm ở cách LlamaIndex khởi tạo connection.")

        except Exception as e:
            print(f"❌ LỖI SQL EXECUTION: {e}")
            print("   -> Có thể chưa cài extension vector? Chạy 'CREATE EXTENSION vector;' trong DB xem.")

if __name__ == "__main__":
    debug_raw_sql()