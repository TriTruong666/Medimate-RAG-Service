import sys
import os
import json
from sqlalchemy import create_engine, text

# Setup đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from app.core.config import settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from app.services.model_loader import get_embed_model, get_llm

def final_diagnosis():
    print("\n========== 1. KIỂM TRA DATABASE (SQL Thuần) ==========")
    db_url = settings.RAG_DB_URL
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Check bảng
        result = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_name = 'embeddings'"))
        if result.scalar() == 0:
            print("❌ LỖI CHÍ MẠNG: Không tìm thấy bảng 'embeddings'!")
            return
        
        # Check cột 'text' (đã đổi tên chưa)
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'embeddings' AND column_name = 'text'"))
        if not result.first():
            print("❌ LỖI CHÍ MẠNG: Không tìm thấy cột 'text' trong bảng 'embeddings'. Ông chưa đổi tên cột hoặc chưa chạy lệnh SQL ALTER TABLE!")
            return
        
        # Check dữ liệu
        count = conn.execute(text("SELECT count(*) FROM embeddings")).scalar()
        print(f"✅ Bảng 'embeddings' OK. Tổng số dòng: {count}")
        
        # Check vector null
        null_vec = conn.execute(text("SELECT count(*) FROM embeddings WHERE embedding IS NULL")).scalar()
        print(f"ℹ️ Số dòng có vector NULL (Node Cha): {null_vec}")
        print(f"ℹ️ Số dòng có vector (Node Con): {count - null_vec}")
        
        if (count - null_vec) == 0:
            print("❌ LỖI: Không có dòng nào có vector! Chạy lại script reindex.py ngay.")
            return

    print("\n========== 2. KIỂM TRA RETRIEVAL (LlamaIndex) ==========")
    try:
        # Giả lập y hệt config API
        vector_store = PGVectorStore.from_params(
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_SERVER,
            password=settings.POSTGRES_PASSWORD,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            table_name="embeddings",
            embed_dim=384, # MiniLM
        )
        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            embed_model=get_embed_model()
        )
        
        # Test Search
        retriever = index.as_retriever(similarity_top_k=5)
        nodes = retriever.retrieve("Giai đoạn 1")
        
        if not nodes:
            print("❌ LỖI: Search trả về 0 kết quả! Do lệch Model Embedding hoặc Vector trong DB là rác.")
            return
        else:
            print(f"✅ Search OK! Tìm thấy {len(nodes)} nodes.")
            print(f"   -> Top 1 Score: {nodes[0].score}")
            print(f"   -> Content: {nodes[0].text[:100]}...")

    except Exception as e:
        print(f"❌ Exception Retrieval: {e}")
        return

    print("\n========== 3. KIỂM TRA GENERATION (LLM) ==========")
    try:
        from llama_index.core import PromptTemplate
        
        # Prompt Template TEST ĐƠN GIẢN
        qa_template = PromptTemplate(
            "Context:\n{context_str}\n\nQuestion: {query_str}\nAnswer:"
        )
        
        query_engine = index.as_query_engine(
            llm=get_llm(),
            text_qa_template=qa_template
        )
        
        print("⏳ Đang hỏi LLM (Chờ tí)...")
        response = query_engine.query("Giai đoạn 1")
        print(f"✅ LLM Trả lời:\n{response}")
        
    except Exception as e:
        print(f"❌ Exception LLM: {e}")

if __name__ == "__main__":
    final_diagnosis()