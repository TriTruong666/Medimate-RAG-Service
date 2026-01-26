import os
import hashlib
import shutil
from sqlalchemy import desc
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models import Document, Embedding
from app.schemas.document import DocumentResponse
from app.services.file_service import process_file_in_memory
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.schema import NodeRelationship
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
class DocumentService:
    file_types = ["pdf", "docx", "txt", "text", "doc", "json"]
    _chunk_sizes = [2048, 512, 128]
    _node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=_chunk_sizes)
    _embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL)
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
        
            all_nodes = DocumentService._node_parser.get_nodes_from_documents(llama_docs)

            leaf_nodes = get_leaf_nodes(all_nodes)

            leaf_ids = {n.node_id for n in leaf_nodes}

            db.query(Embedding).filter(Embedding.document_id == doc.id).delete()
            
            embedding_records = []

            for node in all_nodes:
                # -- Xử lý Parent ID --
                parent_id = None
                if NodeRelationship.PARENT in node.relationships:
                    parent_id = node.relationships[NodeRelationship.PARENT].node_id

                # -- Xác định xem có phải Leaf không --
                is_leaf = node.node_id in leaf_ids
                
                # -- Tính Vector --
                # Logic quan trọng: CHỈ tính vector cho Leaf Node (tiết kiệm 2/3 tài nguyên)
                vector_data = None
                if is_leaf:
                    # Đây là đoạn "Đang tính toán Vector..." trong code cũ
                    vector_data = DocumentService._embed_model.get_text_embedding(node.get_content())
                
                # -- Xác định Level (Mẹo: dựa vào độ dài text hoặc chunk size) --
                # Level 0 = Leaf (nhỏ nhất), Level càng cao càng to
                current_level = 0
                if not is_leaf:
                    # Nếu không phải leaf, ta check chunk_size để đoán level
                    # Ví dụ: size ~ 2048 là level 2, size ~ 512 là level 1
                    # Hoặc đơn giản: 0 là Leaf, 1 là Non-Leaf
                    current_level = 1 

                # -- Tạo Record --
                emb_record = Embedding(
                    document_id=doc.id,
                    content=node.get_content(),
                    embedding=vector_data,  # Leaf thì có vector, Cha thì NULL
                    metadata_=node.metadata,
                    
                    # Mapping ID chuẩn để sau này retrieve
                    node_id=node.node_id,
                    parent_node_id=parent_id,
                    
                    level=current_level,
                    chunk_size=len(node.get_content())
                )
                embedding_records.append(emb_record)

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

        