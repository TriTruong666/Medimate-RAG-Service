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
                # Điểm này là điểm similarity, càng thấp càng giống
                score = 1.0 - float(row[2])
                
                node = TextNode(text=row[1], id_=str(row[0]))
                nodes.append(NodeWithScore(node=node, score=score))

        return nodes

def get_engine(streaming: bool = True):
   
    connection_string = settings.RAG_DB_URL
    
    retriever = CustomPostgresRetriever(
        connection_string=connection_string,
        embed_model=get_embed_model(),
        top_k=5
    )

    qa_prompt_str = (
        "<|im_start|>system\n"
        "You are a helpful and friendly AI assistant named Medimate AI.\n"
        "Your primary objective is to assist users by answering their questions in **Vietnamese**.\n"
        "Please provide clear, concise, detail and accurate responses based on the context provided below."
        "\n"
        "STRICTLY FOLLOW THESE RULES:\n"
        "1. **Language**: You MUST answer in **Vietnamese**, regardless of whether the context or the user's question is in English.\n"
        "2. **Grounding**: Answer the question based **ONLY** on the provided context below. Do NOT use your prior knowledge or external information.\n"
        "3. **Missing Info**: If the answer is NOT in the context, you must strictly reply: 'Xin lỗi, dữ liệu hiện tại của tôi không có thông tin về vấn đề này.' (Do not try to make up an answer).\n"
        "4. **Formatting**: Use Markdown to structure your answer:\n"
        "   - Use **Headings** for sections.\n"
        "   - Use **Bold** for key terms.\n"
        "   - Use **Bullet points** for lists.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Given the context information and not prior knowledge, answer the query in Vietnamese.\n"
        "Query: {query_str}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    text_qa_template = PromptTemplate(qa_prompt_str)

  
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=get_llm(),
        text_qa_template=text_qa_template,
        streaming=streaming
    )

    return query_engine

def initialize_global_engine(streaming: bool = True):
    return get_engine(streaming)