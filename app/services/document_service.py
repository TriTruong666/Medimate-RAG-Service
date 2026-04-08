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
    def process_document(db: Session, document_id: str):
        doc = db.query(Document).filter(Document.id == document_id).first()
        embed_model = get_embed_model(db)
        if not doc:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
        
        return DocumentService._ingest_document(db, doc, embed_model)

    @staticmethod
    def process_collection(db: Session, collection_id: str):
        """Xử lý nạp toàn bộ tài liệu trong một collection (Bulk Ingest)"""
        docs = db.query(Document)\
                 .filter(Document.collection_id == collection_id)\
                 .filter(Document.status.in_(["uploaded", "failed"]))\
                 .all()
        
        if not docs:
            return {"message": "Không có tài liệu nào cần xử lý trong collection này."}

        embed_model = get_embed_model(db)
        success_count = 0
        error_count = 0

        print(f"--- Bắt đầu xử lý bulk cho Collection {collection_id} ({len(docs)} tài liệu)...")
        
        for doc in docs:
            try:
                DocumentService._ingest_document(db, doc, embed_model)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"--- Lỗi khi xử lý file {doc.doc_name}: {e}")

        return {
            "message": f"Đã xử lý xong collection. Thành công: {success_count}, Thất bại: {error_count}",
            "data": {
                "total": len(docs),
                "success": success_count,
                "failed": error_count
            }
        }

    @staticmethod
    def _ingest_document(db: Session, doc: Document, embed_model):
        """Logic lõi để xử lý và nạp một tài liệu vào vector db"""
        if doc.status == "indexed" or doc.status == "sent":
            return {"message": "Tài liệu đã được xử lý từ trước."}

        if doc.status == "indexing":
            raise HTTPException(status_code=400, detail="Tài liệu đang trong quá trình xử lý...")

        try:
            doc.status = "indexing"
            db.commit()

            if not os.path.exists(doc.file_path):
                raise FileNotFoundError(f"Không tìm thấy file: {doc.file_path}")
            
            with open(doc.file_path, "rb") as f:
                file_bytes = f.read()

            llama_docs = process_file_in_memory(doc.doc_name, file_bytes)
            if not llama_docs:
                raise ValueError("Không thể trích xuất nội dung từ file")
        
            for llama_doc in llama_docs:
                llama_doc.metadata["document_name"] = doc.doc_name
                llama_doc.metadata["category"] = "medical_data"
                
            all_nodes = DocumentService._node_parser.get_nodes_from_documents(llama_docs)
            all_texts = [n.get_content() for n in all_nodes]
            
            # Batch embedding
            all_embeddings = embed_model.get_text_embedding_batch(all_texts)

            # Xóa các embedding cũ nếu có (re-index)
            db.query(Embedding).filter(Embedding.document_id == doc.id).delete()
            
            embedding_records = []
            for i, node in enumerate(all_nodes):
                parent_id = None
                if NodeRelationship.PARENT in node.relationships:
                    parent_id = node.relationships[NodeRelationship.PARENT].node_id

                text_content = node.get_content()
                vector_data = [float(x) for x in all_embeddings[i]]
                
                # Metadata cleaning
                cleaned_metadata = {}
                for k, v in node.metadata.items():
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

            # Bulk insert embeddings
            batch_size = 100
            for i in range(0, len(embedding_records), batch_size):
                batch = embedding_records[i : i + batch_size]
                db.add_all(batch)
                db.commit()

            doc.status = "indexed"
            db.commit()

            return {
                "message": f"Nạp tài liệu {doc.doc_name} thành công",
                "status": "success"
            }

        except Exception as e:
            db.rollback()
            doc.status = "failed"
            db.commit()
            raise e

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

        