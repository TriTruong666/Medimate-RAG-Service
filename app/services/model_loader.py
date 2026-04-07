import os
import torch
import logging
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.services.rag_config_service import RagConfigService
from sqlalchemy.orm import Session
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

llm = None
embed_model = None
_reranker = None

def get_llm(db: Session = None):
    global llm
    if llm is not None:
        return llm
    
    # Nếu lần đầu load mà không có DB thì tạch
    if db is None:
        raise Exception("LLM chưa được khởi tạo. Cần truyền Session DB cho lần đầu!")

    rag_config = RagConfigService.get_rag_config(db)
    model_record = rag_config.default_llm
    
    if not model_record:
        raise Exception("Không có LLM nào được gán trong RagConfig!")

    # Lấy thông số từ model_record config JSONB
    api_key = model_record.config.get("api_key") if model_record.config else None
    model_name = model_record.config.get("model_name") if model_record.config else "models/gemini-2.5-pro"
    
    if not api_key:
        logger.warning(f"Model {model_record.name} thiếu cấu hình api_key, vui lòng cập nhật!")

    print(f"Loading Google GenAI Model: {model_name}")

    os.environ["GOOGLE_API_KEY"] = api_key if api_key else ""

    from llama_index.llms.google_genai import Gemini
    
    llm = Gemini(
        model=model_name,
        temperature=rag_config.temperature,
        max_tokens=model_record.max_output_tokens,
    )
    return llm

_embed_model = None
def get_embed_model(db: Session = None):
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Lấy model name từ settings cho đồng bộ
    model_name = settings.EMBEDDING_MODEL

    print(f"Loading Embedding Model: {model_name} on {device}")
    _embed_model = HuggingFaceEmbedding(
        device=device,
        model_name=model_name,
        cache_folder=os.path.join(os.getcwd(), "app", "models_weights"),
        embed_batch_size=100
    )
    return _embed_model


class MedicalReranker(BaseNodePostprocessor):
    """Custom Reranker using Sentence Transformers CrossEncoder for Medical accuracy."""
    _model: any = None
    _top_n: int = 3

    def __init__(self, model_name: str, top_n: int = 3, device: str = "cpu"):
        super().__init__()
        self._model = CrossEncoder(model_name, device=device)
        self._top_n = top_n

    @classmethod
    def class_name(cls) -> str:
        return "MedicalReranker"

    def _postprocess_nodes(self, nodes, query_bundle):
        if not nodes:
            return []
        
        query_str = query_bundle.query_str
        texts = [node.get_content() for node in nodes]
        
        # BAAI/bge-reranker-v2-m3 returns raw similarity scores
        # show_progress_bar=False để không hiện thanh load mỗi lần hỏi
        scores = self._model.predict([[query_str, text] for text in texts], show_progress_bar=False)
        
        for node, score in zip(nodes, scores):
            # Ép kiểu từ numpy.float32 về float chuẩn Python để tránh lỗi JSON serializable
            node.score = float(score)
            
        nodes.sort(key=lambda x: x.score, reverse=True)
        return nodes[:self._top_n]


def get_reranker(db: Session = None):
    global _reranker
    if _reranker is not None:
        return _reranker
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Reranker Model: BAAI/bge-reranker-v2-m3 on {device}")
    
    _reranker = MedicalReranker(
        model_name="BAAI/bge-reranker-v2-m3", 
        top_n=3,
        device=device
    )
    return _reranker
