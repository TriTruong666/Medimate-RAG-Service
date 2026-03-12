import os
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.core.config import settings

llm = None
embed_model = None


def messages_to_prompt(messages):

    prompt = (
        "<|im_start|>system\n"
        "Yêu cầu thực hiện:\n"
        "- Cung cấp câu trả lời CHI TIẾT, ĐẦY ĐỦ và CỤ THỂ.\n"
        "- Giải thích các luận điểm chính một cách rõ ràng, mạch lạc.\n"
        "- Trả lời hoàn toàn bằng TIẾNG VIỆT.\n"
        "- Văn phong: TRANG TRỌNG, KHÁCH QUAN và CHÍNH XÁC (phù hợp với tính chất tài liệu chính trị).\n"
        "- Nếu thông tin không có trong ngữ cảnh, hãy trả lời chính xác là: 'Tài liệu không cung cấp thông tin về vấn đề này.'.\n"
        "CÁC QUY TẮC CẤM (TUYỆT ĐỐI TUÂN THỦ):\n"
        "1. KHÔNG sử dụng kiến thức bên ngoài (chỉ dựa vào thông tin được cung cấp ở trên).\n"
        "2. KHÔNG được tự suy diễn hoặc bịa đặt thông tin sai lệch.\n"
        "3. Sử dụng định dạng Markdown (In đậm, In nghiêng, Danh sách) để trình bày dễ đọc.\n"
        "<|im_end|>\n"
    )
    # ----------------------

    for message in messages:
        if message.role == "system":
            continue
        elif message.role == "user":
            prompt += f"<|im_start|>user\n{message.content}<|im_end|>\n"
        elif message.role == "assistant":
            prompt += f"<|im_start|>assistant\n{message.content}<|im_end|>\n"

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
            # repeat_penalty=1.2 nghĩa là: Nếu lặp lại câu cũ, điểm số sẽ bị chia 1.2 => AI sẽ né câu đó ra
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
    if embed_model is None:
        print(f"Loading Embedding Model: {settings.EMBEDDING_MODEL}")
        embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            cache_folder=os.path.join(os.getcwd(), "app", "models_weights"),
        )
    return embed_model
