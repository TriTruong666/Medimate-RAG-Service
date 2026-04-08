from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
from app.models import Collection, Document
from app.schemas.collection import CollectionCreate, CollectionUpdate
import math
from uuid import UUID
from typing import List

class CollectionService:
    @staticmethod
    def create_collection(db: Session, collection_in: CollectionCreate):
        # Kiểm tra trùng tên
        existing = db.query(Collection).filter(Collection.name == collection_in.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tên collection đã tồn tại!")
        
        new_collection = Collection(
            name=collection_in.name,
            description=collection_in.description,
            is_active=collection_in.is_active
        )
        db.add(new_collection)
        db.commit()
        db.refresh(new_collection)
        return new_collection

    @staticmethod
    def get_list_collections(db: Session, page: int, limit: int, search_query: str = None):
        skip = (page - 1) * limit
        query = db.query(Collection)

        if search_query:
            search = f"%{search_query}%"
            query = query.filter(Collection.name.ilike(search))

        total_records = query.count()
        collections = query.order_by(desc(Collection.created_at))\
                           .offset(skip)\
                           .limit(limit)\
                           .all()
        
        total_pages = math.ceil(total_records / limit) if limit > 0 else 1
        
        return {
            "items": collections,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "limit": limit,
                "total_records": total_records
            }
        }

    @staticmethod
    def get_collection_by_id(db: Session, collection_id: UUID):
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise HTTPException(status_code=404, detail="Collection không tồn tại")
        return collection

    @staticmethod
    def update_collection(db: Session, collection_id: UUID, collection_in: CollectionUpdate):
        collection = CollectionService.get_collection_by_id(db, collection_id)
        
        if collection_in.name is not None:
            # Kiểm tra trùng tên nếu đổi tên
            if collection_in.name != collection.name:
                existing = db.query(Collection).filter(Collection.name == collection_in.name).first()
                if existing:
                    raise HTTPException(status_code=400, detail="Tên collection đã tồn tại!")
            collection.name = collection_in.name
            
        if collection_in.description is not None:
            collection.description = collection_in.description
            
        if collection_in.is_active is not None:
            collection.is_active = collection_in.is_active
            
        db.commit()
        db.refresh(collection)
        return collection

    @staticmethod
    def delete_collection(db: Session, collection_id: UUID):
        collection = CollectionService.get_collection_by_id(db, collection_id)
        db.delete(collection)
        db.commit()
        return {"message": "Xóa collection thành công"}

    @staticmethod
    def assign_documents(db: Session, collection_id: UUID, document_ids: List[UUID]):
        # Kiểm tra collection tồn tại
        CollectionService.get_collection_by_id(db, collection_id)
        
        # Cập nhật collection_id cho danh sách documents (Add only)
        db.query(Document)\
          .filter(Document.id.in_(document_ids))\
          .update({Document.collection_id: collection_id}, synchronize_session=False)
        
        db.commit()
        return {"message": f"Đã gán {len(document_ids)} tài liệu vào collection"}

    @staticmethod
    def sync_documents(db: Session, collection_id: UUID, document_ids: List[UUID]):
        """Sửa list document: Gán chính xác danh sách này vào collection, gỡ bỏ những cái cũ."""
        # Kiểm tra collection tồn tại
        CollectionService.get_collection_by_id(db, collection_id)
        
        # 1. Gỡ bỏ những cái cũ
        db.query(Document)\
          .filter(Document.collection_id == collection_id)\
          .update({Document.collection_id: None}, synchronize_session=False)
        
        # 2. Gán list mới
        if document_ids:
            db.query(Document)\
              .filter(Document.id.in_(document_ids))\
              .update({Document.collection_id: collection_id}, synchronize_session=False)
        
        db.commit()
        return {"message": "Đã cập nhật chính xác danh sách tài liệu trong collection"}
