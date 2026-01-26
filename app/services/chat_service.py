import json
from llama_index.core.base.response.schema import StreamingResponse

class ChatService:
    @staticmethod
    def chat_stream_generator(query_engine, question: str):
        """
        Input: Engine đã cấu hình AutoMerging + Câu hỏi
        Output: Generator bắn ra từng dòng JSON
        """
        if not query_engine:
            yield json.dumps({"type": "error", "content": "Engine chưa sẵn sàng"}) + "\n"
            return

        try:
            # 1. Query vào Engine (Lúc này nó sẽ chạy AutoMergingRetriever ngầm)
            streaming_response = query_engine.query(question)

            # 2. Bắn chữ (Text Streaming)
            for token in streaming_response.response_gen:
                data = {
                    "type": "text", 
                    "content": token
                }
                yield json.dumps(data) + "\n"

            # 3. Bắn nguồn (Source Nodes) - Sau khi text chạy xong
            formatted_sources = []
            if streaming_response.source_nodes:
                for node_with_score in streaming_response.source_nodes:
                    node = node_with_score.node
                    meta = node.metadata
                    
                    # Lấy thông tin file
                    formatted_sources.append({
                        "filename": meta.get("filename") or meta.get("doc_name") or "N/A",
                        "page": meta.get("page_label", "N/A"),
                        "score": round(node_with_score.score, 4) if node_with_score.score else 0.0,
                        # Trích 1 đoạn ngắn để show
                        "snippet": node.get_content()[:150] + "..." 
                    })

            # Gói tin cuối cùng chứa Source
            yield json.dumps({
                "type": "source",
                "data": formatted_sources
            }) + "\n"

        except Exception as e:
            print(f"Lỗi Chat: {e}")
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"