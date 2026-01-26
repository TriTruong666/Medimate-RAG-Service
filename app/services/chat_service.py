import json
from llama_index.core.base.response.schema import StreamingResponse

class ChatService:
    @staticmethod
    def chat_stream_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine rỗng"}, ensure_ascii=False) + "\n"
            return

        try:
           
            response_obj = query_engine.query(question)
            
          
            if hasattr(response_obj, "response_gen"):
               
                for token in response_obj.response_gen:
                    if token:    
                        yield json.dumps({"type": "text", "content": token}, ensure_ascii=False) + "\n"
            else:
               
                content = getattr(response_obj, "response", str(response_obj))
                yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"

            source_data = ChatService._format_sources(response_obj.source_nodes)
            yield source_data.strip() + "\n"

        except Exception as e:
            print(f"Lỗi Stream: {e}")
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    @staticmethod
    def chat_completion_generator(query_engine, question: str):
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}, ensure_ascii=False) + "\n"
            return
        
        try:
            response_obj = query_engine.query(question)
            final_text = ""
            
            if hasattr(response_obj, 'response_gen'):
                for token in response_obj.response_gen:
                    final_text += token
            else:             
                final_text = response_obj.response or ""

            if not final_text.strip() or final_text.strip() == "Empty Response":
                final_text = "Xin lỗi, tôi tìm thấy tài liệu liên quan nhưng không thể tổng hợp câu trả lời (Lỗi Model). Dưới đây là các nguồn tham khảo:"

            yield json.dumps({
                "type": "text",
                "content": final_text 
            }, ensure_ascii=False) + "\n"

            yield ChatService._format_sources(response_obj.source_nodes) + "\n"

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
