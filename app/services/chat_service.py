import json
from llama_index.core.base.response.schema import StreamingResponse

class ChatService:
    @staticmethod
    def chat_stream_generator(query_engine, question: str):
       
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}) + "\n"
            return

        try:
            streaming_response = query_engine.query(question)

            for token in streaming_response.response_gen:
                data = {
                    "type": "text", 
                    "content": token
                }
                yield json.dumps(data) + "\n"

            formatted_sources = []
            if streaming_response.source_nodes:
                for node_with_score in streaming_response.source_nodes:
                    node = node_with_score.node
                    meta = node.metadata
                    
                    formatted_sources.append({
                        "filename": meta.get("filename") or meta.get("doc_name") or "N/A",
                        "page": meta.get("page_label", "N/A"),
                        "score": round(node_with_score.score, 4) if node_with_score.score else 0.0,
                    
                        "snippet": node.get_content()[:150] + "..." 
                    })

            yield json.dumps({
                "type": "source",
                "data": formatted_sources
            }) + "\n"

        except Exception as e:
            print(f"Lỗi Chat: {e}")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"