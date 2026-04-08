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

        sql = text(
            """
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
        """
        )

        nodes = []
        with self._engine.connect() as conn:
            results = conn.execute(
                sql, {"vector": vector_str, "limit": self._top_k, "query": query_str}
            ).fetchall()

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
        engine=rag_engine, embed_model=embed_model, top_k=config.top_k + 5
    )

    # Wrap prompt để yêu cầu Citation bắt buộc
    markdown_rules = """

====================
QUY TẮC TRẢ LỜI VÀ ĐỊNH DẠNG:

1. ĐỊNH DẠNG MARKDOWN CHUYÊN NGHIỆP:
   - Sử dụng thẻ Heading (##, ###) để phân chia các phần một cách khoa học.
   - Sử dụng Bullet points hoặc Numbered lists để liệt kê.
   - **In đậm** các thuật ngữ quan trọng hoặc cảnh báo.

2. PHONG CÁCH THEO NGỮ CẢNH TÀI LIỆU:
   - Khi dữ liệu thuộc Collection **"Giao tiếp"**: Hãy trả lời ngắn gọn, lịch sự, tập trung vào chào hỏi và hướng dẫn chung. TUYỆT ĐỐI không chèn các câu hỏi chẩn đoán y khoa dồn dập.
   - Khi dữ liệu thuộc Collection **"Khẩn cấp"**: Hãy đặt các hành động cứu hộ (như GỌI 115) lên dòng đầu tiên. Sử dụng giọng văn quyết liệt, rõ ràng.
   - Luôn ưu tiên sự thấu cảm nhưng phải giữ được sự súc tích. Tránh lặp lại thông tin không cần thiết.

3. QUY TẮC KHÁC:
   - Trả lời trực tiếp vào câu hỏi.
   - KHÔNG CẦN chèn trích dẫn mã nguồn cuối bài.
====================
"""

    citation_wrapper = config.prompt_template + markdown_rules
    text_qa_template = PromptTemplate(citation_wrapper)

    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=llm_model,
        node_postprocessors=[reranker],
        text_qa_template=text_qa_template,
        streaming=streaming,
    )

    return query_engine


def initialize_global_engine(streaming: bool = True, ai_model_id: str = None):

    db = SessionLocal()
    try:

        return get_engine(db=db, streaming=streaming, ai_model_id=ai_model_id)
    finally:

        db.close()
