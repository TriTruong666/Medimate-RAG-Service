import sys
import os

from app.core.config import settings
from app.services.file_service import load_documents_from_folder, process_file_in_memory
from app.services.rag_engine import ingest_documents, get_index
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
    print("2. Nạp thêm dữ liệu mới")

    choice = input("Mời bạn chọn (1/2): ").strip()

    documents = []

    if choice == "2":
        mode = (
            input("Bạn muốn nạp từ đâu? (cpu: quét folder / ram: giả lập upload): ")
            .strip()
            .lower()
        )

        if mode == "cpu":
            print("\nĐang quét folder uploads...")
            documents = load_documents_from_folder()

        elif mode == "ram":
            if not os.path.exists(settings.UPLOAD_DIR):
                print("Thư mục uploads không tồn tại!")
            else:
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

        if documents:
            print(
                f"\nĐang nạp {len(documents)} tài liệu vào ChromaDB (Lâu hay nhanh tùy độ dày)..."
            )
            ingest_documents(documents)
        else:
            print("\nKhông tìm thấy tài liệu mới nào.")

    print("\nĐang khởi động Model AI & Database...")
    index = get_index()

    if index is None:
        print(
            "Lỗi: Chưa có dữ liệu (Index). Vui lòng bỏ file vào data/uploads và chọn 'y' để học."
        )
        return

    # Tạo Query Engine (Bộ máy trả lời)
    qa_template_str = (
        "Below is contextual information extracted from the document.:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Based on the above context, please answer the question: {query_str}\n\n"
        "Requirements:\n"
        "- Provide a DETAILED, COMPLETE, and SPECIFIC answer.\n"
        "- Explain the main points clearly, don't give abrupt answers.\n"
        "- Present your ideas clearly and concisely; if you have multiple points, use bullet points.\n"
        "- Answer entirely in English.\n"
        "- If the document does NOT contain the information, state unequivocally that it cannot be found.\n"
    )
    qa_template = PromptTemplate(qa_template_str)

    query_engine = index.as_query_engine(
        similarity_top_k=3,
        response_mode="refine",
        text_qa_template=qa_template,
        streaming=True,
    )

    print("\nHỆ THỐNG ĐÃ SẴN SÀNG! (Gõ 'exit' để thoát)")
    print("-" * 50)

    # BƯỚC 3: VÒNG LẶP CHAT
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

            for token in streaming_response.response_gen:
                print(token, end="", flush=True)

            print()

        except Exception as e:
            print(f"\nCó lỗi xảy ra: {e}")


if __name__ == "__main__":
    main()
