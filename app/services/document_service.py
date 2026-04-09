import os
import hashlib
import shutil
from sqlalchemy import desc
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.services.model_loader import get_embed_model
from sqlalchemy.orm import Session
from app.models import Document, Embedding, Collection
from app.schemas.document import DocumentResponse
from app.services.file_service import process_file_in_memory
from app.services.sse_service import SSEService
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeRelationship, TextNode
import re
import json
from sqlalchemy import func


class DocumentService:
    file_types = ["pdf", "docx", "txt", "text", "doc", "json", "md"]
    # Medical-aware chunker: Chia chunk lớn tránh đứt gãy thực thể y khoa (thuốc - liều lượng)
    _node_parser = SentenceSplitter(
        chunk_size=1024, chunk_overlap=150, paragraph_separator="\n\n"
    )

    @staticmethod
    def save_upload_file(db: Session, file: UploadFile, filename: str):
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in DocumentService.file_types:
            raise HTTPException(
                status_code=400,
                detail=f"Loại file không hợp lệ. Chỉ chấp nhận: {', '.join(DocumentService.file_types)}",
            )

        file_checksum = calculate_file_hash(file)

        existed_doc = (
            db.query(Document).filter(Document.checksum == file_checksum).first()
        )

        if existed_doc:
            raise HTTPException(
                status_code=400, detail="File này đã tồn tại trong hệ thống rồi!"
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
    def bulk_save_upload_files(db: Session, files: list[UploadFile]):
        """Hỗ trợ tải lên nhiều tài liệu cùng một lúc"""
        success_list = []
        error_list = []

        for file in files:
            try:
                # Tận dụng logic của hàm đơn lẻ
                res = DocumentService.save_upload_file(db, file, file.filename)
                success_list.append(
                    {
                        "filename": file.filename,
                        "status": "success",
                        "data": res["data"],
                    }
                )
            except HTTPException as e:
                error_list.append(
                    {"filename": file.filename, "status": "failed", "reason": e.detail}
                )
            except Exception as e:
                error_list.append(
                    {"filename": file.filename, "status": "failed", "reason": str(e)}
                )

        return {
            "total": len(files),
            "success_count": len(success_list),
            "error_count": len(error_list),
            "items": success_list + error_list,
        }

    @staticmethod
    def get_list_documents(
        db: Session, page: int, limit: int, search_query: str = None
    ):

        skip = (page - 1) * limit

        query = db.query(Document)

        if search_query:
            search = f"%{search_query}%"
            query = query.filter(Document.doc_name.ilike(search))

        total_records = query.count()

        documents = (
            query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
        )

        import math

        total_pages = math.ceil(total_records / limit) if limit > 0 else 0

        doc_schemas = [DocumentResponse.model_validate(doc) for doc in documents]

        return {
            "items": doc_schemas,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_records": total_records,
            },
        }

    @staticmethod
    def get_uncollected_documents(
        db: Session, page: int, limit: int, search_query: str = None
    ):
        skip = (page - 1) * limit

        query = db.query(Document).filter(Document.collection_id == None)

        if search_query:
            search = f"%{search_query}%"
            query = query.filter(Document.doc_name.ilike(search))

        total_records = query.count()

        documents = (
            query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
        )

        import math

        total_pages = math.ceil(total_records / limit) if limit > 0 else 0

        doc_schemas = [DocumentResponse.model_validate(doc) for doc in documents]

        return {
            "items": doc_schemas,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_records": total_records,
            },
        }

    @staticmethod
    def get_pending_documents(
        db: Session, page: int, limit: int, search_query: str = None
    ):
        skip = (page - 1) * limit

        query = db.query(Document).filter(Document.status.in_(["uploaded", "failed"]))

        if search_query:
            search = f"%{search_query}%"
            query = query.filter(Document.doc_name.ilike(search))

        total_records = query.count()

        documents = (
            query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
        )

        import math

        total_pages = math.ceil(total_records / limit) if limit > 0 else 0

        doc_schemas = [DocumentResponse.model_validate(doc) for doc in documents]

        return {
            "items": doc_schemas,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_records": total_records,
            },
        }

    @staticmethod
    async def process_document(db: Session, document_id: str, client_id: str = None):
        doc = db.query(Document).filter(Document.id == document_id).first()
        embed_model = get_embed_model(db)
        if not doc:
            if client_id:
                await SSEService.send_alert(
                    client_id, "Lỗi", "Tài liệu không tồn tại", "error"
                )
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")

        return await DocumentService._ingest_document(db, doc, embed_model, client_id)

    @staticmethod
    async def process_collection(
        db: Session, collection_id: str, client_id: str = None
    ):
        """Xử lý nạp toàn bộ tài liệu trong một collection (Bulk Ingest)"""
        docs = (
            db.query(Document)
            .filter(Document.collection_id == collection_id)
            .filter(Document.status.in_(["uploaded", "failed"]))
            .all()
        )

        if not docs:
            if client_id:
                await SSEService.send_alert(
                    client_id, "Thông báo", "Không có tài liệu nào cần xử lý.", "info"
                )
            return {"message": "Không có tài liệu nào cần xử lý trong collection này."}

        embed_model = get_embed_model(db)
        success_count = 0
        error_count = 0
        total = len(docs)

        if client_id:
            await SSEService.send_log(
                client_id, f"Bắt đầu xử lý bulk cho {total} tài liệu...", progress=0
            )

        for i, doc in enumerate(docs):
            try:
                if client_id:
                    await SSEService.send_log(
                        client_id,
                        f"Đang xử lý ({i+1}/{total}): {doc.doc_name}",
                        progress=int((i / total) * 100),
                    )
                await DocumentService._ingest_document(db, doc, embed_model, client_id)
                success_count += 1
            except Exception as e:
                error_count += 1
                if client_id:
                    await SSEService.send_log(
                        client_id, f"Lỗi file {doc.doc_name}: {str(e)}", status="error"
                    )

        if client_id:
            await SSEService.send_log(client_id, "Hoàn tất xử lý bulk.", progress=100)
            await SSEService.send_alert(
                client_id,
                "Hoàn tất",
                f"Đã xử lý xong {success_count} tài liệu.",
                "success",
            )

        return {
            "message": f"Đã xử lý xong collection. Thành công: {success_count}, Thất bại: {error_count}",
            "data": {"total": total, "success": success_count, "failed": error_count},
        }

    @staticmethod
    async def bulk_process_documents(
        db: Session, document_ids: list[str], client_id: str = None
    ):
        """Xử lý nạp danh sách tài liệu được chọn (Bulk Ingest by IDs)"""
        docs = (
            db.query(Document)
            .filter(Document.id.in_(document_ids))
            .all()
        )

        if not docs:
            if client_id:
                await SSEService.send_alert(
                    client_id, "Thông báo", "Không tìm thấy tài liệu nào để xử lý.", "info"
                )
            return {"message": "Không tìm thấy tài liệu nào để xử lý."}

        embed_model = get_embed_model(db)
        success_count = 0
        error_count = 0
        total = len(docs)

        if client_id:
            await SSEService.send_log(
                client_id, f"Bắt đầu xử lý bulk cho {total} tài liệu...", progress=0
            )

        for i, doc in enumerate(docs):
            try:
                if client_id:
                    await SSEService.send_log(
                        client_id,
                        f"Đang xử lý ({i+1}/{total}): {doc.doc_name}",
                        progress=int((i / total) * 100),
                    )
                await DocumentService._ingest_document(db, doc, embed_model, client_id)
                success_count += 1
            except Exception as e:
                error_count += 1
                if client_id:
                    await SSEService.send_log(
                        client_id, f"Lỗi file {doc.doc_name}: {str(e)}", status="error"
                    )

        if client_id:
            await SSEService.send_log(client_id, "Hoàn tất xử lý bulk.", progress=100)
            await SSEService.send_alert(
                client_id,
                "Hoàn tất",
                f"Đã xử lý xong {success_count} tài liệu.",
                "success",
            )

        return {
            "message": f"Đã xử lý xong danh sách. Thành công: {success_count}, Thất bại: {error_count}",
            "data": {"total": total, "success": success_count, "failed": error_count},
        }

    @staticmethod
    async def _ingest_document(
        db: Session, doc: Document, embed_model, client_id: str = None
    ):
        """Logic lõi để xử lý và nạp một tài liệu vào vector db"""
        if doc.status == "indexed" or doc.status == "sent":
            return {"message": "Tài liệu đã được xử lý từ trước."}

        if doc.status == "indexing":
            raise HTTPException(
                status_code=400, detail="Tài liệu đang trong quá trình xử lý..."
            )

        try:
            if client_id:
                await SSEService.send_log(
                    client_id, f"Đang chuẩn bị nạp: {doc.doc_name}"
                )

            doc.status = "indexing"
            db.commit()

            if not os.path.exists(doc.file_path):
                raise FileNotFoundError(f"Không tìm thấy file: {doc.file_path}")

            with open(doc.file_path, "rb") as f:
                file_bytes = f.read()

            if client_id:
                await SSEService.send_log(
                    client_id, f"Đang trích xuất nội dung: {doc.doc_name}"
                )

            llama_docs = process_file_in_memory(doc.doc_name, file_bytes)
            if not llama_docs:
                raise ValueError("Không thể trích xuất nội dung từ file")

            # Lấy thông tin Collection để gán vào metadata
            collection_name = "N/A"
            if doc.collection_id:
                col = db.query(Collection).get(doc.collection_id)
                if col:
                    collection_name = col.name

            for llama_doc in llama_docs:
                llama_doc.metadata["document_name"] = doc.doc_name
                llama_doc.metadata["collection_id"] = (
                    str(doc.collection_id) if doc.collection_id else "N/A"
                )
                llama_doc.metadata["category"] = collection_name

            all_nodes = DocumentService._node_parser.get_nodes_from_documents(
                llama_docs
            )
            all_texts = [n.get_content() for n in all_nodes]

            if client_id:
                await SSEService.send_log(
                    client_id, f"Đang tạo embedding ({len(all_texts)} chunks)..."
                )

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
                        cleaned_metadata[k] = [
                            x.item() if hasattr(x, "item") else x for x in v
                        ]
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
                    chunk_size=len(text_content),
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
                "status": "success",
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
