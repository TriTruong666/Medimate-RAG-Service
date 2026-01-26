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
                # row[0]: id, row[1]: text, row[2]: distance
                # Cosine Similarity = 1 - Distance
                score = 1.0 - float(row[2])
                
                node = TextNode(text=row[1], id_=str(row[0]))
                nodes.append(NodeWithScore(node=node, score=score))

        return nodes

def get_engine():
   
    connection_string = settings.RAG_DB_URL
    
    retriever = CustomPostgresRetriever(
        connection_string=connection_string,
        embed_model=get_embed_model(),
        top_k=5
    )

    qa_prompt_str = (
        "<|im_start|>system\n"
        "You are a English AI assistant.. "
        "Your primary language is English. "
        "Even if the document or question is in Vietnamese, you MUST answer in English.. "
        "Explain detail by English.\n"
        "They will call you Meditate AI and you are helpful and friendly.\n"
        "STRICTLY FOLLOW THESE RULES:\n"
        "1. You must answer the question based ONLY on the provided context below.\n"
        "2. Do NOT use your prior knowledge or external information.\n"
        "3. If the answer is not in the context, say: 'My data does not contain information about this issue.'.\n"
        "4. PRESENTATION GUIDELINES (Markdown must be used):\n"
        "- Use headings, subheadings, bullet points, and numbered lists where appropriate to enhance readability.\n"
        "- Use **bold** and *italic* text to emphasize key points.\n"
        "- Include code snippets within triple backticks for clarity.\n"
        "<|im_end|>\n"
    )
    text_qa_template = PromptTemplate(qa_prompt_str)

  
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=get_llm(),
        text_qa_template=text_qa_template,
        streaming=True
    )

    return query_engine

def initialize_global_engine():
    return get_engine()