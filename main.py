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
        print("\nLỖI NGHIÊM TRỌNG: Không có dữ liệu (Index là None).")
        print("Vui lòng kiểm tra lại folder 'data' hoặc chọn Option 2 để nạp lại.")
        return

    # --- SETUP CHAT ENGINE ---
    qa_template_str = (
        "Dưới đây là thông tin ngữ cảnh được trích xuất từ tài liệu:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Dựa trên ngữ cảnh trên, hãy trả lời câu hỏi: {query_str}\n\n"
        "Yêu cầu thực hiện:\n"
        "- Cung cấp câu trả lời CHI TIẾT, ĐẦY ĐỦ và CỤ THỂ.\n"
        "- Giải thích các luận điểm chính một cách rõ ràng, mạch lạc.\n"
        "- Trả lời hoàn toàn bằng TIẾNG VIỆT.\n"
        "- Văn phong: TRANG TRỌNG, KHÁCH QUAN và CHÍNH XÁC (phù hợp với tính chất tài liệu chính trị).\n"
        "- Nếu thông tin không có trong ngữ cảnh, hãy trả lời chính xác là: 'Tài liệu không cung cấp thông tin về vấn đề này.'.\n"
        "CÁC QUY TẮC CẤM (TUYỆT ĐỐI TUÂN THỦ):\n"
        "1. KHÔNG sử dụng kiến thức bên ngoài (chỉ dựa vào thông tin được cung cấp ở trên).\n"
        "2. KHÔNG được tự suy diễn hoặc bịa đặt thông tin sai lệch.\n"
        "3. Sử dụng định dạng Markdown (In đậm, In nghiêng, Danh sách) để trình bày dễ đọc.\n"
    )
    qa_template = PromptTemplate(qa_template_str)

    query_engine = get_hierarchical_query_engine(index, qa_template)

    if query_engine is None:
        print("Lỗi khởi tạo Engine. Kiểm tra lại log.")
        return

    print("\nHỆ THỐNG ĐÃ SẴN SÀNG! (Gõ 'exit' để thoát)")
    print("-" * 50)

    # --- VÒNG LẶP CHAT ---
    while True:
        try:
            question = input("\nTôi: ")
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
