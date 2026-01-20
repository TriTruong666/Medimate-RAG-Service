import sys
import os

# 1. Thêm đường dẫn hiện tại vào hệ thống để Python tìm thấy thư mục 'app'
sys.path.append(os.getcwd())

# 2. Import lại các hàm từ code cũ của bạn
from app.core.config import settings
from app.services.file_service import load_documents_from_folder
from app.services.rag_engine import ingest_documents, get_index

def main():
    print("==================================================")
    print(f"🤖  HỆ THỐNG RAG COMMAND LINE - {settings.PROJECT_NAME}")
    print("==================================================\n")

    # BƯỚC 1: HỎI CÓ MUỐN HỌC TÀI LIỆU MỚI KHÔNG
    # Kiểm tra xem có cần tạo thư mục không
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR)

    print(f"📁 Folder tài liệu: {settings.UPLOAD_DIR}")
    choice = input("❓ Bạn có muốn quét và học tài liệu mới không? (y/n): ").strip().lower()

    if choice == 'y':
        print("\n[1/2] 📖 Đang đọc file...")
        documents = load_documents_from_folder()
        
        if documents:
            print(f"[2/2] 🧠 Đang nạp vào bộ nhớ (Embedding)... Vui lòng chờ!")
            # Gọi hàm từ rag_engine.py
            msg = ingest_documents(documents)
            print(f"✅ {msg}")
        else:
            print("⚠️ Không tìm thấy file nào trong thư mục uploads.")

    # BƯỚC 2: LOAD INDEX ĐỂ CHAT
    print("\n⏳ Đang khởi động Model AI & Database...")
    index = get_index()

    if index is None:
        print("❌ Lỗi: Chưa có dữ liệu (Index). Vui lòng bỏ file vào data/uploads và chọn 'y' để học.")
        return

    # Tạo Query Engine (Bộ máy trả lời)
    query_engine = index.as_query_engine(
        similarity_top_k=3,    # Lấy 3 đoạn văn bản liên quan nhất
        response_mode="compact", # Trả lời ngắn gọn súc tích

        system_prompt=(
            "Bạn là một trợ lý AI thông minh, chuyên hỗ trợ tư vấn dựa trên tài liệu."
            " Nhiệm vụ của bạn là trả lời câu hỏi của người dùng HOÀN TOÀN BẰNG TIẾNG VIỆT."
            " Dựa sát vào ngữ cảnh được cung cấp để trả lời ngắn gọn, súc tích."
        )
    )

    print("\n✅ HỆ THỐNG ĐÃ SẴN SÀNG! (Gõ 'exit' để thoát)")
    print("-" * 50)

    # BƯỚC 3: VÒNG LẶP CHAT
    while True:
        try:
            question = input("\n👤 Bạn: ")
            
            if question.lower() in ['exit', 'quit', 'thoat']:
                print("👋 Tạm biệt!")
                break
            
            if not question.strip():
                continue

            # Thực hiện hỏi AI
            print("🤖 AI: Đang suy nghĩ...", end="\r")
            response = query_engine.query(question)
            
            # Xóa dòng đang suy nghĩ
            print(" " * 30, end="\r")
            print(f"🤖 AI: {response}")

        except Exception as e:
            print(f"\n❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()