import json
import time
from llama_index.core.base.response.schema import StreamingResponse

class ChatService:
    @staticmethod
    def chat_stream_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine rỗng"}, ensure_ascii=False) + "\n"
            return

        try:
            start_time = time.time()
            print(f"\n[{time.strftime('%X')}] [STREAM] Bắt đầu truy xuất RAG & LLM cho câu hỏi: '{question}' ...")
           
            response_obj = query_engine.query(question)
            
            rag_time = time.time() - start_time
            print(f"[{time.strftime('%X')}] [STREAM] Truy xuất xong! Bắt đầu trả kết quả (Thời gian RAG: {rag_time:.2f}s)")
          
            if hasattr(response_obj, "response_gen"):
               
                for token in response_obj.response_gen:
                    if token:    
                        yield json.dumps({"type": "text", "content": token}, ensure_ascii=False) + "\n"
            else:
               
                content = getattr(response_obj, "response", str(response_obj))
                yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"

            total_time = time.time() - start_time
            print(f"[{time.strftime('%X')}] [STREAM] Hoàn thành luồng stream. Tổng thời gian: {total_time:.2f}s\n")

        except Exception as e:
            print(f"Lỗi Stream: {e}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    @staticmethod
    def chat_completion_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}, ensure_ascii=False) + "\n"
            return
        
        try:
            start_time = time.time()
            print(f"\n[{time.strftime('%X')}] [COMPLETION] Bắt đầu xử lý câu hỏi: '{question}' ...")
            
            # Cho phép lấy thẳng response (nhanh hơn loop generator)
            response_obj = query_engine.query(question)
            
            final_text = str(response_obj.response) if hasattr(response_obj, 'response') else str(response_obj)
            
            if not final_text.strip() or final_text.strip() == "Empty Response":
                final_text = "Xin lỗi, tôi tìm thấy tài liệu liên quan nhưng không thể tổng hợp câu trả lời."

            yield json.dumps({
                "type": "text",
                "content": final_text 
            }, ensure_ascii=False) + "\n"

            total_time = time.time() - start_time
            print(f"[{time.strftime('%X')}] [COMPLETION] Hoàn thành câu trả lời. Tổng thời gian: {total_time:.2f}s\n")

        except Exception as e:
            print(f"Lỗi Completion: {e}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    @staticmethod
    def _format_sources(source_nodes):
        
        formatted_sources = []
        if source_nodes:
            for node_with_score in source_nodes:
                node = node_with_score.node
                meta = node.metadata
                
                formatted_sources.append({
                    "filename": meta.get("filename") or meta.get("doc_name") or "N/A",
                    "page": meta.get("page_label", "N/A"),
                    "score": round(node_with_score.score, 4) if node_with_score.score else 0.0,

                    "snippet": node.get_content()[:150] + "..." 
                })
        
        return json.dumps({
            "type": "source",
            "data": formatted_sources
        })


"""
Nhớ tắt các print debug trước khi deploy nhé!
ensure_ascii=True để tránh lỗi mã hóa tiếng Việt trong JSON
"""