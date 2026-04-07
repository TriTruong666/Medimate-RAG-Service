import sys
import logging
from typing import List
from sqlalchemy import create_engine, text

from llama_index.core import PromptTemplate
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.callbacks import CallbackManager
from app.core.db.rag_database import SessionLocal, rag_engine
from app.services.rag_config_service import RagConfigService
from app.services.model_loader import get_llm, get_embed_model, get_reranker
from app.core.config import settings


logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class CustomPostgresRetriever(BaseRetriever):
    def __init__(self, engine, embed_model, top_k: int = 5):
        self._engine = engine
        self._embed_model = embed_model
        self._top_k = top_k
        super().__init__()

    def _retrieve(self, query_bundle) -> List[NodeWithScore]:
        query_str = query_bundle.query_str
        
        query_embedding = self._embed_model.get_text_embedding(query_str)
        
        vector_str = str(query_embedding)

        sql = text("""
        WITH semantic_search AS (
            SELECT id, text, metadata, (1.0 - (embedding <=> :vector)) AS semantic_score
            FROM embeddings
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :vector
            LIMIT :limit
        ),
        keyword_search AS (
            SELECT id, text, metadata, ts_rank(fts_vector, websearch_to_tsquery('simple', :query)) AS keyword_score
            FROM embeddings
            WHERE fts_vector @@ websearch_to_tsquery('simple', :query)
            ORDER BY keyword_score DESC
            LIMIT :limit
        )
        SELECT 
            COALESCE(s.id, k.id) AS id,
            COALESCE(s.text, k.text) AS text,
            COALESCE(s.metadata, k.metadata) AS metadata,
            (COALESCE(s.semantic_score, 0.0) * 0.7 + COALESCE(k.keyword_score, 0.0) * 0.3) AS combined_score
        FROM semantic_search s
        FULL OUTER JOIN keyword_search k ON s.id = k.id
        ORDER BY combined_score DESC
        LIMIT :limit;
        """)

        nodes = []
        with self._engine.connect() as conn:
            results = conn.execute(sql, {"vector": vector_str, "limit": self._top_k, "query": query_str}).fetchall()
            
            for row in results:
                score = float(row[3])
                # Đưa thêm metadata vào text node
                node_metadata = row[2] if isinstance(row[2], dict) else {}
                node = TextNode(text=row[1], id_=str(row[0]), metadata=node_metadata)
                nodes.append(NodeWithScore(node=node, score=score))

        return nodes

def get_engine(db, streaming: bool = True, ai_model_id: str = None):
    if db is None:
        raise Exception("Session DB không được để trống!")

    
    config = RagConfigService.get_rag_config(db)

    connection_string = settings.RAG_DB_URL
    
    
    embed_model = get_embed_model(db) 
    llm_model = get_llm(db, ai_model_id=ai_model_id) 
    reranker = get_reranker(db)
    
    # Lấy thêm để reranker có dữ liệu lọc (Top 10 -> Reranker -> Top 5)
    retriever = CustomPostgresRetriever(
        engine=rag_engine,
        embed_model=embed_model,
        top_k=config.top_k + 5 
    )

    # Wrap prompt để yêu cầu Citation bắt buộc
    markdown_rules = """

====================
QUY TẮC TRẢ LỜI VÀ ĐỊNH DẠNG BẮT BUỘC:

1. ĐỊNH DẠNG MARKDOWN CHUẨN:
   - Sử dụng thẻ Heading (##, ###) để chia bố cục các phần rõ ràng.
   - Sử dụng Bullet points (-) hoặc Numbered lists (1. 2. 3.) để liệt kê.
   - In đậm (**từ khóa**) các ý chính hoặc cảnh báo quan trọng.
   - Nếu có đoạn code, BẮT BUỘC phải đặt trong khối code block chuẩn (ví dụ: ```csharp ... ```).
   - Phải xuống dòng rõ ràng (cách nhau 1 dòng trống) giữa các đoạn văn.

2. CÁCH TRÍCH DẪN (CITATIONS):
   - TUYỆT ĐỐI KHÔNG chèn trực tiếp tên file vào nội dung bài viết (Cấm dùng kiểu: [Nguồn: abc.docx]).
   - Khi tham khảo thông tin từ context, chỉ đánh số thứ tự trong ngoặc vuông ở cuối câu. Ví dụ: "...yêu cầu chứng chỉ SSL/TLS [1][2]."

3. DANH SÁCH TÀI LIỆU THAM KHẢO:
   - Ở dưới cùng của câu trả lời, bắt buộc tạo một mục "### Nguồn tham khảo:"
   - Liệt kê lại các tài liệu đã dùng tương ứng với số thứ tự.
   - Ví dụ format:
     [1] To enable HTTPS on your server.docx
     [2] Security_Guidelines.pdf
====================
"""
    
    citation_wrapper = config.prompt_template + markdown_rules
    text_qa_template = PromptTemplate(citation_wrapper)

    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=llm_model,
        node_postprocessors=[reranker],
        text_qa_template=text_qa_template,
        streaming=streaming
    )

    return query_engine

def initialize_global_engine(streaming: bool = True, ai_model_id: str = None):
   
    db = SessionLocal()
    try:
      
        return get_engine(db=db, streaming=streaming, ai_model_id=ai_model_id)
    finally:
        
        db.close()