import logging

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class ChatService:
    @staticmethod
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
            if not final_text.strip() or final_text.strip() == "Empty Response":
                final_text = "Xin lỗi, tôi tìm thấy tài liệu liên quan nhưng không thể tổng hợp câu trả lời (Lỗi Model). Dưới đây là các nguồn tham khảo:"
            
            sources = []
            if getattr(response_obj, "source_nodes", None):
                sources = ChatService._format_sources(response_obj.source_nodes)
            
            return {
                "answer": final_text,
                "sources": sources
            }
        except Exception:
            logger.exception("Lỗi chat completion")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi chat completion")

    @staticmethod
    def _format_sources(source_nodes):
        
        formatted_sources = []
        if source_nodes:
            for node_with_score in source_nodes:
                node = node_with_score.node
                meta = node.metadata or {}
                raw_score = float(node_with_score.score) if node_with_score.score is not None else 0.0
                distance = max(0.0, 1.0 - raw_score)
                normalized_score = 1.0 / (1.0 + distance)
                
                formatted_sources.append({
                    "filename": meta.get("filename") or meta.get("doc_name") or "N/A",
                    "page": meta.get("page_label", "N/A"),
                    "score": round(normalized_score, 4),
                    "raw_score": round(raw_score, 4),
                    "distance": round(distance, 4),
                    "snippet": node.get_content()[:150] + "..." 
                })
        
        return formatted_sources


    # @staticmethod
    # def chat_stream_generator(query_engine, question: str):
    #     if not query_engine:
    #         yield json.dumps({"type": "error", "content": "Engine rỗng"}, ensure_ascii=False) + "\n"
    #         return

    #     try:
           
    #         response_obj = query_engine.query(question)
            
          
    #         if hasattr(response_obj, "response_gen"):
               
    #             for token in response_obj.response_gen:
    #                 if token:    
    #                     yield json.dumps({"type": "text", "content": token}, ensure_ascii=False) + "\n"
    #         else:
               
    #             content = getattr(response_obj, "response", str(response_obj))
    #             yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"

    #         source_data = ChatService._format_sources(response_obj.source_nodes)
    #         yield source_data.strip() + "\n"

    #     except Exception as e:
    #         print(f"Lỗi Stream: {e}")
    #         yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    # @staticmethod
    # def chat_completion_generator(query_engine, question: str):
    #     if not query_engine:
    #         yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}, ensure_ascii=False) + "\n"
    #         return
        
    #     try:
    #         response_obj = query_engine.query(question)
    #         final_text = ""
            
    #         if hasattr(response_obj, 'response_gen'):
    #             for token in response_obj.response_gen:
    #                 final_text += token
    #         else:             
    #             final_text = response_obj.response or ""

    #         if not final_text.strip() or final_text.strip() == "Empty Response":
    #             final_text = "Xin lỗi, tôi tìm thấy tài liệu liên quan nhưng không thể tổng hợp câu trả lời (Lỗi Model). Dưới đây là các nguồn tham khảo:"

    #         yield json.dumps({
    #             "type": "text",
    #             "content": final_text 
    #         }, ensure_ascii=False) + "\n"

    #         yield ChatService._format_sources(response_obj.source_nodes) + "\n"

    #     except Exception as e:
    #         print(f"Lỗi Completion: {e}")
    #         yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    # @staticmethod
    # def _format_sources(source_nodes):
        
    #     formatted_sources = []
    #     if source_nodes:
    #         for node_with_score in source_nodes:
    #             node = node_with_score.node
    #             meta = node.metadata
                
    #             formatted_sources.append({
    #                 "filename": meta.get("filename") or meta.get("doc_name") or "N/A",
    #                 "page": meta.get("page_label", "N/A"),
    #                 "score": round(node_with_score.score, 4) if node_with_score.score else 0.0,

    #                 "snippet": node.get_content()[:150] + "..." 
    #             })
        
    #     return json.dumps({
    #         "type": "source",
    #         "data": formatted_sources
    #     })


"""
Nhớ tắt các print debug trước khi deploy nhé!
ensure_ascii=True để tránh lỗi mã hóa tiếng Việt trong JSON
"""