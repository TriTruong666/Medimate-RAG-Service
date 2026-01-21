import os
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from app.core.config import settings
from app.services.model_loader import get_llm, get_embed_model


def get_index():
    """
    Hàm này kết nối tới ChromaDB và trả về Index.
    Nếu DB chưa có gì, nó trả về Index rỗng.
    Nếu DB đã có dữ liệu, nó tự load lên (rất nhanh).
    """
    # 1. Load Model & Embed (như cũ)
    llm = get_llm()
    embed_model = get_embed_model()

    # Cấu hình toàn cục
    Settings.llm = llm
    Settings.embed_model = embed_model

    # 2. Khởi tạo ChromaDB Client (Chế độ Persistent - Lưu xuống đĩa)
    # Nếu thư mục chưa có, nó tự tạo.
    db = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)

    # 3. Tạo hoặc lấy Collection (giống như Bảng trong SQL)
    # Tên collection đặt là 'mpf_rag_col' (tùy ý)
    chroma_collection = db.get_or_create_collection("mpf_rag_col")

    # 4. Tạo Vector Store
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # 5. Gắn vào Storage Context
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 6. Tạo Index từ Vector Store
    # LlamaIndex tự biết: nếu DB có data thì dùng, chưa có thì tạo mới.
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
        embed_model=embed_model,  # Cần truyền lại embed_model vào đây
    )

    return index


def ingest_documents(documents):
    """
    Nạp tài liệu vào ChromaDB
    """
    if not documents:
        return "Không có tài liệu để nạp."

    print("Đang kết nối tới ChromaDB...")
    index = get_index()

    print(f"Đang tính toán Vector và lưu vào DB ({len(documents)} docs)...")

    # Vì index đã kết nối với Chroma, lệnh insert này sẽ ghi thẳng vào DB
    for doc in documents:
        index.insert(doc)

    # Không cần lệnh index.storage_context.persist() nữa!
    # ChromaDB tự động lưu (Auto-save).

    return f"Đã lưu {len(documents)} tài liệu vào ChromaDB thành công!"
