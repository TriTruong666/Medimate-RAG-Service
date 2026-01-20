import os
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.core.config import settings

llm = None
embed_model = None

# --- 1. HÀM ĐỊNH DẠNG PROMPT CHO QWEN (QUAN TRỌNG) ---
# Qwen dùng chuẩn ChatML: <|im_start|>...<|im_end|>
# Nếu không có cái này, model sẽ không biết đâu là lời bạn, đâu là lời nó => Bị lặp
def messages_to_prompt(messages):
    prompt = ""
    for message in messages:
        if message.role == 'system':
            prompt += f"<|im_start|>system\n{message.content}<|im_end|>\n"
        elif message.role == 'user':
            prompt += f"<|im_start|>user\n{message.content}<|im_end|>\n"
        elif message.role == 'assistant':
            prompt += f"<|im_start|>assistant\n{message.content}<|im_end|>\n"
    
    # Mồi cho AI bắt đầu trả lời
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
            
            # --- 2. CẤU HÌNH THÔNG MINH HƠN ---
            temperature=0.1,       # Giảm sáng tạo xuống thấp để trả lời đúng trọng tâm
            max_new_tokens=512,    # Giới hạn độ dài câu trả lời (tránh viết sớ)
            context_window=4096,   # Độ dài ngữ cảnh nhớ được
            
            # --- 3. THUỐC TRỊ BỆNH LẶP TỪ (REPEAT PENALTY) ---
            # repeat_penalty=1.2 nghĩa là: Nếu lặp lại câu cũ, điểm số sẽ bị chia 1.2 => AI sẽ né câu đó ra
            generate_kwargs={
                "repeat_penalty": 1.2, 
                "top_p": 0.9,
                "stop": ["<|im_end|>", "User:"] # Gặp ký tự này là CÂM NGAY
            },
            
            # Gắn hàm định dạng prompt đã viết ở trên vào
            messages_to_prompt=messages_to_prompt,
            completion_to_prompt=completion_to_prompt,
            
            verbose=False
        )
    return llm

def get_embed_model():
    global embed_model
    if embed_model is None:
        print(f"Loading Embedding Model: {settings.EMBEDDING_MODEL}")
        embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            cache_folder=os.path.join(os.getcwd(), "app", "models_weights")
        )
    return embed_model