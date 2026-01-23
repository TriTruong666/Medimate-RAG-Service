import sys
import os

from app.core.config import settings
from app.services.file_service import load_documents_from_folder, process_file_in_memory
from app.services.rag_engine import (
    ingest_documents,
    get_index,
    get_hierarchical_query_engine,
)
from llama_index.core import PromptTemplate

sys.path.append(os.getcwd())


def print_banner():
    logo = r"""
███╗   ███╗███████╗██████╗ ██╗███╗   ███╗ █████╗ ████████╗███████╗
████╗ ████║██╔════╝██╔══██╗██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║█████╗  ██║  ██║██║██╔████╔██║███████║   ██║   █████╗  
██║╚██╔╝██║██╔══╝  ██║  ██║██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║███████╗██████╔╝██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

██████╗  █████╗  ██████╗     ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗
██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝
██████╔╝███████║██║  ███╗    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  
██╔══██╗██╔══██║██║   ██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  
██║  ██║██║  ██║╚██████╔╝    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝
    """
    print(logo)


def main():
    print_banner()

    print("1. Chat ngay")
    print("2. Nạp thêm dữ liệu mới (Xóa cũ, học lại từ đầu)")

    choice = input("Mời bạn chọn (1/2): ").strip()

    # Biến này để lưu index (Bộ não AI)
    index = None

    # --- TRƯỜNG HỢP 1: NẠP DỮ LIỆU ---
    if choice == "2":
        mode = input("Nạp từ đâu? (cpu: folder / ram: giả lập): ").strip().lower()
        documents = []

        if mode == "cpu":
            print("\nĐang quét folder uploads...")
            documents = load_documents_from_folder()

        elif mode == "ram":
            # (Đoạn code đọc file RAM giữ nguyên)
            if os.path.exists(settings.UPLOAD_DIR):
                print("\nĐang xử lý giả lập RAM...")
                all_files = os.listdir(settings.UPLOAD_DIR)
                for filename in all_files:
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    if os.path.isfile(file_path):
                        try:
                            with open(file_path, "rb") as f:
                                file_bytes = f.read()
                            docs = process_file_in_memory(filename, file_bytes)
                            if docs:
                                documents.extend(docs)
                                print(f"Đã đọc: {filename}")
                        except Exception:
                            pass
            else:
                print("Thư mục uploads không tồn tại!")

        if documents:
            print(f"\nĐang nạp {len(documents)} tài liệu vào ChromaDB...")

            # --- KHÚC QUAN TRỌNG NHẤT ---
            # Hứng lấy index trả về từ hàm ingest luôn
            # Không load lại từ đĩa nữa => Tránh lỗi 100%
            index = ingest_documents(documents)

        else:
            print("\nKhông tìm thấy tài liệu nào để nạp.")

    # --- TRƯỜNG HỢP 2: CHƯA CÓ INDEX (Do chọn Chat ngay hoặc Ingest lỗi) ---
    # Lúc này mới bắt buộc phải load từ ổ cứng
    if index is None:
        print("\nĐang khởi động Model & Load dữ liệu từ ổ cứng...")
        index = get_index()

    # --- KIỂM TRA CUỐI CÙNG ---
    if index is None:
        print("\n❌ LỖI NGHIÊM TRỌNG: Không có dữ liệu (Index là None).")
        print("Vui lòng kiểm tra lại folder 'data' hoặc chọn Option 2 để nạp lại.")
        return

    # --- SETUP CHAT ENGINE ---
    qa_template_str = (
        "Below is contextual information extracted from the document.:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Based on the above context, please answer the question: {query_str}\n\n"
        "Requirements:\n"
        "- Provide a DETAILED, COMPLETE, and SPECIFIC answer.\n"
        "- Explain the main points clearly.\n"
        "- Answer entirely in English.\n"
        "- If information is missing, say: 'The documentation doesn't have information on this issue.'.\n"
        "PROHIBITED RULES:\n"
        "1. Do not use external knowledge.\n"
        "2. Don't make things up.\n"
        "3. Use Markdown (Bold, Italic, Lists) for readability.\n"
    )
    qa_template = PromptTemplate(qa_template_str)

    # Gọi hàm tạo Engine Mẹ Bồng Con
    query_engine = get_hierarchical_query_engine(index, qa_template)

    if query_engine is None:
        print("Lỗi khởi tạo Engine. Kiểm tra lại log.")
        return

    print("\nHỆ THỐNG ĐÃ SẴN SÀNG! (Gõ 'exit' để thoát)")
    print("-" * 50)

    # --- VÒNG LẶP CHAT ---
    while True:
        try:
            question = input("\nTao: ")
            if question.lower() in ["exit", "quit", "thoat"]:
                print("Tạm biệt!")
                break
            if not question.strip():
                continue

            print("AI: ", end="", flush=True)
            streaming_response = query_engine.query(question)

            # Streaming text
            for token in streaming_response.response_gen:
                print(token, end="", flush=True)
            print()

            # [Debug] In ra xem nó lấy thông tin từ những file nào (nếu cần)
            # print("\n[Source Nodes]:")
            # for node in streaming_response.source_nodes:
            #     print(f"- {node.node.metadata.get('file_name', 'Unknown')}: Score {node.score}")

        except Exception as e:
            print(f"\nCó lỗi xảy ra: {e}")


if __name__ == "__main__":
    main()
