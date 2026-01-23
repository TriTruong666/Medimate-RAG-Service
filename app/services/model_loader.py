import os
from llama_index.llms.llama_cpp import LlamaCPP
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.core.config import settings

llm = None
embed_model = None


def messages_to_prompt(messages):

    prompt = (
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
