import sys
import logging
from typing import List
from sqlalchemy import create_engine, text

from llama_index.core import PromptTemplate
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.callbacks import CallbackManager

from app.services.model_loader import get_llm, get_embed_model
from app.core.config import settings

# Setup Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# --- CLASS TỰ CHẾ: CHẠY SQL TRỰC TIẾP ---
class CustomPostgresRetriever(BaseRetriever):
    def __init__(self, connection_string: str, embed_model, top_k: int = 5):
        self._engine = create_engine(connection_string)
        self._embed_model = embed_model
        self._top_k = top_k
        super().__init__()

    def _retrieve(self, query_bundle) -> List[NodeWithScore]:
        query_str = query_bundle.query_str
        
        # 1. Embed câu hỏi
        query_embedding = self._embed_model.get_text_embedding(query_str)
        
        # Convert vector sang dạng string cho Postgres: '[0.1, 0.2, ...]'
        vector_str = str(query_embedding)

        # 2. Chạy SQL Thuần (Đã chứng minh là chạy ngon)
        # Lưu ý: Sửa 'text' thành tên cột đúng trong DB của ông nếu khác
        sql = text(f"""
            SELECT id, text, (embedding <=> '{vector_str}') as distance
            FROM embeddings
            WHERE embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT {self._top_k};
        """)

        nodes = []
        with self._engine.connect() as conn:
            results = conn.execute(sql).fetchall()
            
            for row in results:
                # row[0]: id, row[1]: text, row[2]: distance
                # Cosine Similarity = 1 - Distance
                score = 1.0 - float(row[2])
                
                # Tạo Node object để LlamaIndex hiểu
                node = TextNode(text=row[1], id_=str(row[0]))
                nodes.append(NodeWithScore(node=node, score=score))

        return nodes

def get_engine():
    # 1. Setup Connection
    connection_string = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    
    # 2. Khởi tạo Custom Retriever (Không dùng Index của LlamaIndex nữa)
    retriever = CustomPostgresRetriever(
        connection_string=connection_string,
        embed_model=get_embed_model(),
        top_k=5
    )

    # 3. Setup Prompt (Bắt buộc có để tránh lỗi Empty Response)
    qa_prompt_str = (
        "<|im_start|>system\n"
        "You are a helpful assistant. Answer strictly based on the context below.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        "Context:\n{context_str}\n\n"
        "Question: {query_str}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    text_qa_template = PromptTemplate(qa_prompt_str)

    # 4. Tạo Engine
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=get_llm(),
        text_qa_template=text_qa_template,
        streaming=True
    )

    return query_engine

# Hàm này để tương thích với code gọi cũ của ông
def initialize_global_engine():
    return get_engine()