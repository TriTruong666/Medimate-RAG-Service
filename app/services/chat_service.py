import json
import time
import logging

from fastapi import HTTPException, status
from llama_index.core.base.response.schema import StreamingResponse

logger = logging.getLogger(__name__)


class ChatService:
    @staticmethod
    def build_quick_reply(question: str):
        normalized_question = question.strip().lower()

        # Chỉ giữ lại những trường hợp cực kỳ ngắn hoặc rỗng, còn lại để RAG xử lý
        if not normalized_question or len(normalized_question) < 2:
            return {
                "answer": "Chào bạn! Tôi có thể giúp gì cho bạn về vấn đề y khoa không?",
                "sources": [],
            }
        return None

    @staticmethod
    def chat_stream_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps(
                {"type": "error", "content": "Engine rỗng"}, ensure_ascii=False
            ) + "\n"
            return

        try:
            start_time = time.time()
            print(
                f"\n[{time.strftime('%X')}] [STREAM] Bắt đầu truy xuất RAG & LLM cho câu hỏi: '{question}' ..."
            )

            response_obj = query_engine.query(question)

            rag_time = time.time() - start_time
            print(
                f"[{time.strftime('%X')}] [STREAM] Truy xuất xong! Bắt đầu trả kết quả (Thời gian RAG: {rag_time:.2f}s)"
            )

            if hasattr(response_obj, "response_gen"):

                for token in response_obj.response_gen:
                    if token:
                        yield json.dumps(
                            {"type": "text", "content": token}, ensure_ascii=False
                        ) + "\n"
            else:

                content = getattr(response_obj, "response", str(response_obj))
                yield json.dumps(
                    {"type": "text", "content": content}, ensure_ascii=False
                ) + "\n"

            total_time = time.time() - start_time
            print(
                f"[{time.strftime('%X')}] [STREAM] Hoàn thành luồng stream. Tổng thời gian: {total_time:.2f}s\n"
            )

        except Exception as e:
            print(f"Lỗi Stream: {e}")
            yield json.dumps(
                {"type": "error", "content": str(e)}, ensure_ascii=False
            ) + "\n"

    def build_quick_reply(question: str):
        normalized_question = question.strip().lower()
        greetings = {"hi", "hello", "helo", "hey", "chào", "xin chào"}
        if normalized_question in greetings:
            return {
                "answer": "Chào bạn! Mình có thể giúp gì cho bạn hôm nay?",
                "sources": [],
            }
        if not normalized_question or len(normalized_question) < 3:
            return {
                "answer": "Mình chưa hiểu rõ câu hỏi. Bạn có thể mô tả chi tiết hơn giúp mình không?",
                "sources": [],
            }
        return None

    @staticmethod
    def chat_completion_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps(
                {"type": "error", "content": "Engine chưa sẵn sàng"}, ensure_ascii=False
            ) + "\n"
            return

        try:
            start_time = time.time()
            print(
                f"\n[{time.strftime('%X')}] [COMPLETION] Bắt đầu xử lý câu hỏi: '{question}' ..."
            )

            # Cho phép lấy thẳng response (nhanh hơn loop generator)
            response_obj = query_engine.query(question)

            final_text = (
                str(response_obj.response)
                if hasattr(response_obj, "response")
                else str(response_obj)
            )

            if not final_text.strip() or final_text.strip() == "Empty Response":
                final_text = "Xin lỗi, tôi tìm thấy tài liệu liên quan nhưng không thể tổng hợp câu trả lời."

            yield json.dumps(
                {"type": "text", "content": final_text}, ensure_ascii=False
            ) + "\n"

            total_time = time.time() - start_time
            print(
                f"[{time.strftime('%X')}] [COMPLETION] Hoàn thành câu trả lời. Tổng thời gian: {total_time:.2f}s\n"
            )

        except Exception as e:
            print(f"Lỗi Completion: {e}")
            yield json.dumps(
                {"type": "error", "content": str(e)}, ensure_ascii=False
            ) + "\n"

    @staticmethod
    def chat_completion(query_engine, question: str):
        quick_reply = ChatService.build_quick_reply(question)
        if quick_reply is not None:
            return quick_reply

        if not query_engine:
            raise ValueError("Engine chưa sẵn sàng")

        try:
            response_obj = query_engine.query(question)

            if hasattr(response_obj, "response_gen"):
                final_text = "".join(response_obj.response_gen)
            else:
                final_text = response_obj.response or ""
            sources = []
            if getattr(response_obj, "source_nodes", None):
                sources = ChatService._format_sources(response_obj.source_nodes)

            if not final_text.strip() or final_text.strip() == "Empty Response":
                if not sources:
                    # Nếu không có tài liệu, thay vì trả lời máy móc, ta để AI tự giới thiệu hoặc trả lời tự nhiên
                    # Có thể fallback về một câu trả lời mang tính gợi mở hơn
                    final_text = "Chào bạn! Tôi là trợ lý ảo Medimate AI. Hiện tại tôi chưa tìm thấy tài liệu cụ thể trong cơ sở dữ liệu để giải đáp câu hỏi này một cách chi tiết nhất. Tuy nhiên, tôi vẫn luôn sẵn sàng hỗ trợ bạn các thông tin y khoa cơ bản khác nếu bạn cần!"
                else:
                    final_text = "Xin lỗi, tôi đã tìm thấy một số tài liệu liên quan nhưng không thể tổng hợp được câu trả lời chính xác nhất. Với vai trò là trợ lý y tế Medimate, tôi khuyên bạn nên kiểm tra kỹ các nguồn bên dưới hoặc tham khảo ý kiến bác sĩ chuyên khoa nhé."

            return {"answer": final_text, "sources": sources}
        except Exception:
            logger.exception("Lỗi chat completion")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi chat completion",
            )

    @staticmethod
    def _format_sources(source_nodes):

        formatted_sources = []
        if source_nodes:
            for node_with_score in source_nodes:
                node = node_with_score.node
                meta = node.metadata or {}
                formatted_sources.append(
                    {
                        "filename": meta.get("filename")
                        or meta.get("doc_name")
                        or "N/A",
                        "page": meta.get("page_label", "N/A"),
                        "snippet": node.get_content()[:150] + "...",
                    }
                )

        return formatted_sources
