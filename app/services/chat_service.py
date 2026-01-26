import json
from llama_index.core.base.response.schema import StreamingResponse

class ChatService:
    @staticmethod
    def chat_stream_generator(query_engine, question: str):
        """Xử lý Streaming: Trả về từng token"""
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}) + "\n"
            return

        try:
            streaming_response = query_engine.query(question)

            # 1. Stream Text
            for token in streaming_response.response_gen:
                data = {
                    "type": "text", 
                    "content": token
                }
                yield json.dumps(data) + "\n"

            # 2. Return Sources (Dùng chung logic extract source)
            yield ChatService._format_sources(streaming_response.source_nodes) + "\n"

        except Exception as e:
            print(f"Lỗi Chat Stream: {e}")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    @staticmethod
    def chat_completion_generator(query_engine, question: str):
        """Xử lý Non-Streaming: Chờ xong hết rồi trả về 1 cục"""
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}) + "\n"
            return
        
        try:
            # query_engine này được init với streaming=False, nên trả về object Response
            response = query_engine.query(question)

            # 1. Return Full Text (Trả về nguyên cục text)
            yield json.dumps({
                "type": "text",
                "content": response.response 
            }) + "\n"

            # 2. Return Sources
            yield ChatService._format_sources(response.source_nodes) + "\n"

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
