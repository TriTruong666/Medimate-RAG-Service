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
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from app.services.model_loader import get_llm, get_embed_model

ROOT_DIR = os.getcwd()

CHROMA_DB_DIR = os.path.join(ROOT_DIR, "app", "data", "chroma_db")
METADATA_DIR = os.path.join(ROOT_DIR, "app", "data", "metadata_storage")
CHUNK_SIZES = [1024, 512, 256]


def get_index():
    Settings.llm = get_llm()
    Settings.embed_model = get_embed_model()

    docstore_file = os.path.join(METADATA_DIR, "docstore.json")

    if not os.path.exists(CHROMA_DB_DIR) or not os.path.exists(docstore_file):
        print("LỖI: Không tìm thấy dữ liệu cũ!")
        print(f"(Đã tìm tại: {docstore_file})")
        print("Vui lòng chọn Option 2 để Nạp lại dữ liệu.")
        return None

    print("Đang tải dữ liệu từ ổ cứng...")

    try:

        db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        chroma_collection = db.get_or_create_collection("mpf_rag_col")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        storage_context = StorageContext.from_defaults(
            persist_dir=METADATA_DIR, vector_store=vector_store
        )

        print("Đã load xong dữ liệu.")

        index = load_index_from_storage(
            storage_context, embed_model=Settings.embed_model
        )
        return index

    except Exception as e:
        print(f"❌ Có lỗi khi load dữ liệu: {e}")
        return None


def ingest_documents(documents):
    if not documents:
        return None

    print("\nBắt đầu quá trình ingest...")

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

    db = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    chroma_collection = db.get_or_create_collection("mpf_rag_col")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=CHUNK_SIZES)
    nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(nodes)

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    storage_context.docstore.add_documents(nodes)

    print("Đang tính toán Vector...")
    index = VectorStoreIndex(
        leaf_nodes,
        storage_context=storage_context,
        embed_model=Settings.embed_model,
        show_progress=True,
    )

    storage_context.persist(persist_dir=METADATA_DIR)

    return index


def get_hierarchical_query_engine(index, text_qa_template):
    if index is None:
        return None

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
