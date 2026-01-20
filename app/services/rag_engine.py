from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Settings # <--- MỚI: Thêm Settings
from app.core.config import settings
from app.services.model_loader import get_llm, get_embed_model
import os

def get_index():
    llm = get_llm()
    embed_model = get_embed_model()
    
    # --- CẤU HÌNH TOÀN CỤC (QUAN TRỌNG) ---
    # Ép LlamaIndex dùng model local, không được tìm OpenAI nữa
    Settings.llm = llm                  # <--- MỚI
    Settings.embed_model = embed_model  # <--- MỚI
    # --------------------------------------

    # Kiểm tra nếu đã có Vector DB trên ổ cứng thì load lên
    if os.path.exists(settings.VECTOR_DB_DIR) and os.listdir(settings.VECTOR_DB_DIR):
        # print("🔄 Đang load Index cũ từ ổ cứng...") # (Có thể bỏ comment nếu muốn xem log)
        storage_context = StorageContext.from_defaults(persist_dir=settings.VECTOR_DB_DIR)
        return load_index_from_storage(storage_context, llm=llm, embed_model=embed_model)
    
    return None

def ingest_documents(documents):
    if not documents:
        return "Không có tài liệu nào để học."

    # Gọi hàm này để nó tự set Settings luôn
    index = get_index()
    
    llm = get_llm()
    embed_model = get_embed_model()
    
    # Đảm bảo Settings được set (phòng trường hợp tạo mới)
    Settings.llm = llm
    Settings.embed_model = embed_model

    if index is None:
        print("🆕 Tạo Index mới hoàn toàn...")
        index = VectorStoreIndex.from_documents(
            documents, 
            llm=llm, 
            embed_model=embed_model
        )
    else:
        print("➕ Đang thêm kiến thức mới vào Index cũ...")
        for doc in documents:
            index.insert(doc)
    
    # Lưu xuống ổ cứng
    index.storage_context.persist(persist_dir=settings.VECTOR_DB_DIR)
    
    return "Đã học xong tài liệu mới!"