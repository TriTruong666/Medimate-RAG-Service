import os
import hashlib
import shutil
from sqlalchemy import desc
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.services.model_loader import get_embed_model
from sqlalchemy.orm import Session
from app.models import Document, Embedding
from app.schemas.document import DocumentResponse
from app.services.file_service import process_file_in_memory
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeRelationship, TextNode
import re
import json
from sqlalchemy import func

class DocumentService:
    file_types = ["pdf", "docx", "txt", "text", "doc", "json"]
    # Medical-aware chunker: Chia chunk lớn tránh đứt gãy thực thể y khoa (thuốc - liều lượng)
    _node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=150, paragraph_separator="\n\n")
    @staticmethod
    def save_upload_file(db: Session, file: UploadFile, filename: str):
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in DocumentService.file_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Loại file không hợp lệ. Chỉ chấp nhận: {', '.join(DocumentService.file_types)}"
            )

        file_checksum = calculate_file_hash(file)

        existed_doc = (
            db.query(Document).filter(Document.checksum == file_checksum).first()
        )

        if existed_doc:
            raise HTTPException(
                status_code=400, 
                detail="File này đã tồn tại trong hệ thống rồi!"
            )

        file_path = os.path.join(settings.RAW_UPLOAD_PATH, filename)
        if os.path.exists(file_path):
            filename = f"{file_checksum[:8]}_{filename}"
            file_path = os.path.join(settings.RAW_UPLOAD_PATH, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size_in_bytes = os.path.getsize(file_path)

        new_doc = Document(
            doc_name=filename,
            file_path=file_path,
            type=filename.split(".")[-1],
            status="uploaded",
            checksum=file_checksum,
            file_size=file_size_in_bytes,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        doc_schema = DocumentResponse.model_validate(new_doc)

        return {"message": f"Upload file {filename} thành công", "data": doc_schema}
    
    @staticmethod
    def get_list_documents(db: Session, page: int, limit: int, search_query: str = None):

        skip = (page - 1) * limit
   
        query = db.query(Document)

        if search_query:
            search = f"%{search_query}%"
            query = query.filter(Document.doc_name.ilike(search))

        total_records = query.count()

        documents = query.order_by(desc(Document.created_at))\
                         .offset(skip)\
                         .limit(limit)\
                         .all()
        
        import math
        total_pages = math.ceil(total_records / limit) if limit > 0 else 0
    
        doc_schemas = [DocumentResponse.model_validate(doc) for doc in documents]
    
        return {
            "items": doc_schemas,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_records": total_records
            }
        }
    
    @staticmethod
    def process_document(db: Session, document_id: int):
        doc = db.query(Document).filter(Document.id == document_id).first()
        embed_model = get_embed_model(db)
        if not doc:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
        
        if doc.status == "indexed" or doc.status == "sent":
            raise HTTPException(status_code=400, detail="File này đã học xong rồi")

        if doc.status == "indexing":
            raise HTTPException(status_code=400, detail="File này đang được xử lý, vui lòng chờ")
        try:
            doc.status = "indexing"
            db.commit()

            if not os.path.exists(doc.file_path):
                raise FileNotFoundError(f"Không tìm thấy file trong folder dữ liệu thô: {doc.file_path}")
            
            with open(doc.file_path, "rb") as f:
                file_bytes = f.read()

            llama_docs = process_file_in_memory(doc.doc_name, file_bytes)

            if not llama_docs:
                raise ValueError("Lỗi trích xuất nội dung từ file")
        
            # Trích xuất metadata bổ sung
            for doc_idx, llama_doc in enumerate(llama_docs):
                llama_doc.metadata["document_name"] = doc.doc_name
                # Giả lập extract type cho medical
                llama_doc.metadata["category"] = "medical_data"
                
            all_nodes = DocumentService._node_parser.get_nodes_from_documents(llama_docs)

            print(f"--- Đang bắt đầu quá trình nạp {len(all_nodes)} chunks...")
            
            # Tối ưu: Batch Embedding (Nhanh hơn gấp nhiều lần so với embed từng node)
            all_texts = [n.get_content() for n in all_nodes]
            
            print(f"--- Đang tính toán Vector (BAAI/bge-m3) cho {len(all_nodes)} đoạn văn bản...")
            all_embeddings = embed_model.get_text_embedding_batch(all_texts)
            print(f"--- Đã tính toán xong toàn bộ Vector.")

            db.query(Embedding).filter(Embedding.document_id == doc.id).delete()
            
            embedding_records = []

            for i, node in enumerate(all_nodes):
                parent_id = None
                if NodeRelationship.PARENT in node.relationships:
                    parent_id = node.relationships[NodeRelationship.PARENT].node_id

                text_content = node.get_content()
                
                # Ép kiểu embedding về list float chuẩn
                vector_data = [float(x) for x in all_embeddings[i]]
                
                # Làm sạch Metadata một cách triệt để
                cleaned_metadata = {}
                for k, v in node.metadata.items():
                    # Chuyển đổi mọi loại numpy scalar sang python native
                    if hasattr(v, "item"): 
                        cleaned_metadata[k] = v.item()
                    elif isinstance(v, list):
                        cleaned_metadata[k] = [x.item() if hasattr(x, "item") else x for x in v]
                    else:
                        cleaned_metadata[k] = v

                emb_record = Embedding(
                    document_id=doc.id,
                    text=text_content,
                    embedding=vector_data,
                    metadata_=cleaned_metadata,
                    fts_vector=func.to_tsvector("simple", text_content),
                    node_id=node.node_id,
                    parent_node_id=parent_id,
                    level=0, 
                    chunk_size=len(text_content)
                )
                embedding_records.append(emb_record)
                
                if (i + 1) % 50 == 0:
                    print(f"--- Đã chuẩn bị xong {i + 1}/{len(all_nodes)} records...")

            batch_size = 100
            for i in range(0, len(embedding_records), batch_size):
                batch = embedding_records[i : i + batch_size]
                db.add_all(batch)
                db.commit()

            doc.status = "indexed"
            db.commit()

            return {
                "message": "Nạp dữ liệu thành công",
            }

        except Exception as e:
            db.rollback()
            doc.status = "failed"
            db.commit()
            print(f"Error ingest: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def get_document_by_id(db: Session, document_id: int):
        doc = db.query(Document).filter(Document.id == document_id).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
        
        new_doc = DocumentResponse.model_validate(doc)

        return new_doc

    def delete_document(db: Session, document_id: str):
        try:
            
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")

            
            if os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                    
                except Exception as e:
                    print(f"--- Lỗi khi xoá file vật lý: {e}")
                    
            db.delete(doc)
            db.commit()
            
            return {"message": "Xoá tài liệu thành công"}

        except Exception as e:
            db.rollback()
            print(f"Lỗi khi xoá tài liệu: {e}")
            raise e        

def calculate_file_hash(file: UploadFile) -> str:
    """
    Đọc file và tính ra chuỗi SHA256 (Vân tay duy nhất)
    """
    sha256_hash = hashlib.sha256()

    # Đưa con trỏ về đầu file để đọc từ đầu
    file.file.seek(0)

    # Đọc từng miếng 4KB để không ngốn RAM nếu file to
    for byte_block in iter(lambda: file.file.read(4096), b""):
        sha256_hash.update(byte_block)

    # QUAN TRỌNG: Đọc xong con trỏ đang ở cuối file.
    # Phải đưa về đầu file (seek 0) để lát nữa hàm save còn đọc được mà lưu.
    file.file.seek(0)

    return sha256_hash.hexdigest()

        