import os
import shutil
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    load_index_from_storage,
)
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes

# ĐÃ XÓA DÒNG IMPORT THỪA SimpleDocumentStore TẠI ĐÂY
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from app.services.model_loader import get_llm, get_embed_model

# --- CẤU HÌNH ĐƯỜNG DẪN TUYỆT ĐỐI ---
ROOT_DIR = os.getcwd()

# 1. Folder chứa Vector (ChromaDB)
CHROMA_DB_DIR = os.path.join(ROOT_DIR, "app", "data", "chroma_db")

# 2. Folder chứa Docstore & Metadata (Nơi file docstore.json sẽ nằm)
METADATA_DIR = os.path.join(ROOT_DIR, "app", "data", "metadata_storage")

CHUNK_SIZES = [1024, 512, 256]


def debug_paths():
    print("\n--- KIỂM TRA ĐƯỜNG DẪN ---")
    print(f"📍 Root:     {ROOT_DIR}")
    print(f"📍 Vector:   {CHROMA_DB_DIR}")
    print(f"📍 Metadata: {METADATA_DIR}")
    print("--------------------------\n")


def get_index():
    """Hàm load dữ liệu từ ổ cứng (Option 1)"""
    debug_paths()

    Settings.llm = get_llm()
    Settings.embed_model = get_embed_model()

    # Kiểm tra file docstore.json có tồn tại không
    docstore_file = os.path.join(METADATA_DIR, "docstore.json")

    if not os.path.exists(CHROMA_DB_DIR) or not os.path.exists(docstore_file):
        print("❌ LỖI: Không tìm thấy dữ liệu cũ!")
        print(f"   (Đã tìm tại: {docstore_file})")
        print("👉 Vui lòng chọn Option 2 để Nạp lại dữ liệu.")
        return None

    print("📂 Đang tải dữ liệu từ ổ cứng...")

    try:
        # 1. Kết nối Chroma
        db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        chroma_collection = db.get_or_create_collection("mpf_rag_col")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        # 2. Load Metadata (Docstore)
        # from_defaults(persist_dir=...) sẽ tự load file docstore.json lên
        storage_context = StorageContext.from_defaults(
            persist_dir=METADATA_DIR, vector_store=vector_store
        )

        print("✅ Đã load xong Storage Context.")

        # 3. Dựng lại Index
        index = load_index_from_storage(
            storage_context, embed_model=Settings.embed_model
        )
        return index

    except Exception as e:
        print(f"❌ Có lỗi khi load dữ liệu: {e}")
        return None


def ingest_documents(documents):
    """Hàm nạp dữ liệu mới (Option 2)"""
    if not documents:
        return None

    print("\n--- BẮT ĐẦU QUÁ TRÌNH INGEST ---")
    debug_paths()

    # 1. XÓA DỮ LIỆU CŨ
    print("🧹 Đang dọn dẹp folder data...")
    if os.path.exists(CHROMA_DB_DIR):
        try:
            shutil.rmtree(CHROMA_DB_DIR)
        except:
            pass

    if os.path.exists(METADATA_DIR):
        try:
            shutil.rmtree(METADATA_DIR)
        except:
            pass

    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

    Settings.llm = get_llm()
    Settings.embed_model = get_embed_model()

    # 2. Tạo Chroma Client
    db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    chroma_collection = db.get_or_create_collection("mpf_rag_col")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # 3. Xử lý Node (Cắt nhỏ)
    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=CHUNK_SIZES)
    print("✂️ Đang cắt tài liệu...")
    nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(nodes)
    print(f"   => Tổng nodes: {len(nodes)} | Leaf nodes: {len(leaf_nodes)}")

    # 4. Tạo Storage Context
    # Ở đây nó tự tạo docstore ngầm bên trong, không cần gọi SimpleDocumentStore thủ công nữa
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    storage_context.docstore.add_documents(nodes)

    # 5. Tính Vector & Index
    print("🧠 Đang tính toán Vector...")
    index = VectorStoreIndex(
        leaf_nodes,
        storage_context=storage_context,
        embed_model=Settings.embed_model,
        show_progress=True,
    )

    # 6. LƯU XUỐNG Ổ CỨNG
    print(f"💾 Đang ghi file xuống: {METADATA_DIR}")
    storage_context.persist(persist_dir=METADATA_DIR)

    # Kiểm tra file
    expected_file = os.path.join(METADATA_DIR, "docstore.json")
    if os.path.exists(expected_file):
        size = os.path.getsize(expected_file)
        print(f"✅ THÀNH CÔNG: File docstore.json đã xuất hiện ({size} bytes)")
    else:
        print(f"❌ THẤT BẠI: File docstore.json VẪN KHÔNG CÓ!")

    return index


def get_hierarchical_query_engine(index, text_qa_template):
    if index is None:
        return None

    print("--- Khởi tạo Chat Engine ---")

    base_retriever = index.as_retriever(similarity_top_k=5)

    retriever = AutoMergingRetriever(
        base_retriever,
        storage_context=index.storage_context,
        verbose=True,
    )

    query_engine = RetrieverQueryEngine.from_args(
        retriever,
        llm=get_llm(),
        text_qa_template=text_qa_template,
        streaming=True,
    )

    return query_engine
