from llama_index.core import VectorStoreIndex, StorageContext, PromptTemplate
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.postgres import PGVectorStore
from app.services.model_loader import get_llm, get_embed_model
from app.core.config import settings

def get_hierarchical_query_engine(index):
    if index is None:
        return None

    base_retriever = index.as_retriever(similarity_top_k=5)

    retriever = AutoMergingRetriever(
        base_retriever,
        storage_context=index.storage_context,
        verbose=True,   # Tắt khi lên prod
    )

    qa_prompt_str = (
        "<|im_start|>system\n"
        "You are an AI assistant named Medimate AI. Your primary language is English.\n"
        "Even if the document or question is in Vietnamese, you MUST answer in English.\n"
        "STRICTLY FOLLOW THESE RULES:\n"
        "1. Answer based ONLY on the context provided below.\n"
        "2. Do NOT use outside knowledge.\n"
        "3. If the answer is not in the context, say: 'My data does not contain information about this issue.'\n"
        "4. Use Markdown (bold, lists, code blocks) for clarity.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"  # <--- CHỖ NÀY ĐỂ NHÉT DỮ LIỆU TÌM ĐƯỢC
        "---------------------\n"
        "Given the context information and not prior knowledge, answer the query.\n"
        "Query: {query_str}\n" # <--- CHỖ NÀY ĐỂ NHÉT CÂU HỎI
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    # Bọc trong class PromptTemplate
    text_qa_template = PromptTemplate(qa_prompt_str)
    
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