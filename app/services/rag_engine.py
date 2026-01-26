from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.postgres import PGVectorStore
from app.services.model_loader import get_llm, get_embed_model
from app.core.config import settings

def get_hierarchical_query_engine(index, text_qa_template):
    if index is None:
        return None

    base_retriever = index.as_retriever(similarity_top_k=5)

    retriever = AutoMergingRetriever(
        base_retriever,
        storage_context=index.storage_context,
        verbose=False,   # Tắt khi lên prod
    )

    query_engine = RetrieverQueryEngine.from_args(
        retriever,
        llm=get_llm(),
        text_qa_template=text_qa_template,
        streaming=True,
    )

    return query_engine

def initialize_global_engine():

    vector_store = PGVectorStore.from_params(
        database=settings.POSTGRES_DB,
        host=settings.POSTGRES_SERVER,
        password=settings.POSTGRES_PASSWORD,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        table_name="embeddings", 
        embed_dim=384,
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=get_embed_model()
    )
    
    return get_hierarchical_query_engine(index)