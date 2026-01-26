import os
import torch
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.core.config import settings

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


# -----------------------------------------------------


def get_llm():
    global llm
    if llm is None:
        print(f"Loading LLM from: {settings.MODEL_PATH}")

        llm = LlamaCPP(
            model_path=settings.MODEL_PATH,
            temperature=0.1,  # Giảm sáng tạo xuống thấp để trả lời đúng trọng tâm
            max_new_tokens=512,  # Giới hạn độ dài câu trả lời (tránh viết sớ)
            context_window=3900,  # Độ dài ngữ cảnh nhớ được(máy mạnh cứ nhân đôi lên)
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


def get_embed_model():
    global embed_model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if embed_model is None:
        print(f"Loading Embedding Model: {settings.EMBEDDING_MODEL}")
        embed_model = HuggingFaceEmbedding(
            device=device,
            model_name=settings.EMBEDDING_MODEL,
            cache_folder=os.path.join(os.getcwd(), "app", "models_weights"),
            embed_batch_size=100
        )
    return embed_model
