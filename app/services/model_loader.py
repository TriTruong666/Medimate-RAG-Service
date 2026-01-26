import os
import torch
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.services.rag_config_service import RagConfigService
from sqlalchemy.orm import Session
llm = None
embed_model = None


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
        max_new_tokens=getattr(config, 'max_tokens', 512), # Dùng getattr phòng hờ field name khác
        context_window=getattr(config, 'context_window', 4096),
        generate_kwargs={
            "repeat_penalty": 1.1,
            "top_p": 0.9,
            "stop": ["<|im_end|>", "User:"],
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
        model_name=config.embedding_model,
        cache_folder=os.path.join(os.getcwd(), "app", "models_weights"),
        embed_batch_size=100
    )
    return _embed_model
