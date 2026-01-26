import json
from llama_index.core.base.response.schema import StreamingResponse

class ChatService:
    @staticmethod
    def chat_stream_generator(query_engine, question: str):
        """Xử lý Streaming: Trả về từng token (Bao cân cả lỗi Non-streaming)"""
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}, ensure_ascii=False) + "\n"
            return

        try:
            
            response_obj = query_engine.query(question)
         
            if not response_obj.source_nodes or str(response_obj).strip() == "Empty Response":
                fallback_msg = "Xin lỗi, dữ liệu hiện tại của tôi không có thông tin về vấn đề này."
                # Giả lập streaming trả về câu xin lỗi
                yield json.dumps({"type": "text", "content": fallback_msg}, ensure_ascii=False) + "\n"
                yield ChatService._format_sources([]) + "\n"
                return
          
            if isinstance(response_obj, StreamingResponse):
                
                for token in response_obj.response_gen:
                    data = {
                        "type": "text", 
                        "content": token
                    }
                    yield json.dumps(data, ensure_ascii=False) + "\n"
            else:
               
                data = {
                    "type": "text", 
                    "content": response_obj.response
                }
                yield json.dumps(data, ensure_ascii=False) + "\n"

            yield ChatService._format_sources(response_obj.source_nodes) + "\n"

        except Exception as e:
            print(f"Lỗi Chat Stream: {e}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    @staticmethod
    def chat_completion_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}) + "\n"
            return
        
        try:
           
            response_obj = query_engine.query(question)
                       
            if not response_obj.source_nodes or str(response_obj).strip() == "Empty Response":
                
                fallback_message = "Xin lỗi, dữ liệu hiện tại của tôi không có thông tin về vấn đề này."
                
                yield json.dumps({
                    "type": "text", 
                    "content": fallback_message
                }, ensure_ascii=False) + "\n"
                
                # Trả về source rỗng
                yield ChatService._format_sources([]) + "\n"
                return 
        
            final_text = ""
            if hasattr(response_obj, 'response_gen'): 
                for token in response_obj.response_gen:
                    final_text += token
            else:
                final_text = response_obj.response

            yield json.dumps({
                "type": "text",
                "content": final_text 
            }, ensure_ascii=False) + "\n"

            yield ChatService._format_sources(response_obj.source_nodes) + "\n"

        except Exception as e:
            print(f"Lỗi Chat Completion: {e}")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

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
