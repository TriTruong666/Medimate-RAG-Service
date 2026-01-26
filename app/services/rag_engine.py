import sys
import logging
from typing import List
from sqlalchemy import create_engine, text

from llama_index.core import PromptTemplate
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.callbacks import CallbackManager
from app.core.db.rag_database import SessionLocal
from app.services.rag_config_service import RagConfigService


from app.services.model_loader import get_llm, get_embed_model
from app.core.config import settings


logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class CustomPostgresRetriever(BaseRetriever):
    def __init__(self, connection_string: str, embed_model, top_k: int = 5):
        self._engine = create_engine(connection_string)
        self._embed_model = embed_model
        self._top_k = top_k
        super().__init__()

    def _retrieve(self, query_bundle) -> List[NodeWithScore]:
        query_str = query_bundle.query_str
        
        query_embedding = self._embed_model.get_text_embedding(query_str)
        
        vector_str = str(query_embedding)

        
        sql = text("""
        SELECT id, text, (embedding <=> :vector) as distance
        FROM embeddings
        WHERE embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT :limit;
        """)

        
        nodes = []
        with self._engine.connect() as conn:
            results = conn.execute(sql, {"vector": vector_str, "limit": self._top_k}).fetchall()
            
            for row in results:
                # Điểm này là điểm similarity, càng thấp càng giống
                score = 1.0 - float(row[2])
                
                node = TextNode(text=row[1], id_=str(row[0]))
                nodes.append(NodeWithScore(node=node, score=score))

        return nodes

def get_engine(db, streaming: bool = True):
    if db is None:
        # Dòng này thực ra sẽ không bao giờ chạy tới nếu gọi từ initialize_global_engine
        raise Exception("Session DB không được để trống!")

    # 1. Lấy config từ DB
    config = RagConfigService.get_rag_config(db)

    connection_string = settings.RAG_DB_URL
    
    # 2. QUAN TRỌNG: Truyền db vào get_embed_model và get_llm
    embed_model = get_embed_model(db) # <--- Sửa ở đây
    llm_model = get_llm(db) # Nếu hàm get_llm của ông cũng cần config từ DB thì truyền db vào luôn
    
    retriever = CustomPostgresRetriever(
        connection_string=connection_string,
        embed_model=embed_model,
        top_k=config.top_k # Nên dùng top_k từ DB luôn cho linh hoạt
    )

    text_qa_template = PromptTemplate(config.prompt_template)

    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=llm_model,
        text_qa_template=text_qa_template,
        streaming=streaming
    )

    return query_engine

def initialize_global_engine(streaming: bool = True):
   
    db = SessionLocal()
    try:
      
        return get_engine(db=db, streaming=streaming)
    finally:
        
        db.close()