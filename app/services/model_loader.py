import os
import torch
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.services.rag_config_service import RagConfigService
from sqlalchemy.orm import Session
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from sentence_transformers import CrossEncoder

llm = None
embed_model = None
_reranker = None


def messages_to_prompt(messages):
    prompt = "" 
    for message in messages:
        if message.role == "system":
            prompt += f"<|im_start|>system\n{message.content}<|im_end|>\n"
        elif message.role == "user":
            prompt += f"<|im_start|>user\n{message.content}<|im_end|>\n"
        elif message.role == "assistant":
            prompt += f"<|im_start|>assistant\n{message.content}<|im_end|>\n"

    # Đảm bảo kết thúc để AI biết đến lượt nó nói
    if not prompt.endswith("<|im_start|>assistant\n"):
        prompt += "<|im_start|>assistant\n"

    return prompt

def completion_to_prompt(completion):
    return f"<|im_start|>user\n{completion}<|im_end|>\n<|im_start|>assistant\n"


def get_llm(db: Session = None):
    global llm
    if llm is not None:
        return llm
    
    # Nếu lần đầu load mà không có DB thì tạch
    if db is None:
        raise Exception("LLM chưa được khởi tạo. Cần truyền Session DB cho lần đầu!")

    config = RagConfigService.get_rag_config(db)
    print(f"Loading LLM from: {config.llm_model}")

    llm = LlamaCPP(
        model_path=config.llm_model,
        temperature=config.temperature,
        max_new_tokens=getattr(config, 'max_tokens', 512), 
        context_window=getattr(config, 'context_window', 4096),
        generate_kwargs={
            "repeat_penalty": 1.1,
            "top_p": 0.9,
            "stop": ["<|im_end|>", "User:"],
        },
        model_kwargs={
            "n_gpu_layers": -1,  # Đẩy toàn bộ model vào GPU (nếu có)
            "n_batch": 512,      # Xử lý 512 token cùng lúc (tăng tốc prompt eval)
            "n_ctx": getattr(config, 'context_window', 4096)
        },
        messages_to_prompt=messages_to_prompt,
        completion_to_prompt=completion_to_prompt,
        verbose=False,
    )
    return llm

_embed_model = None
def get_embed_model(db: Session = None):
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    
    if db is None:
        raise Exception("Embed model chưa được khởi tạo. Cần truyền Session DB cho lần khởi tạo đầu tiên!")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    config = RagConfigService.get_rag_config(db)

    print(f"Loading Embedding Model: {config.embedding_model} on {device}")
    _embed_model = HuggingFaceEmbedding(
        device=device,
        model_name=config.embedding_model if config.embedding_model else "BAAI/bge-m3",
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
