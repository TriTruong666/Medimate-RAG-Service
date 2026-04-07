# API Development Pipeline Skill

This document defines the standard procedure and best practices for building a complete, production-ready API endpoint within this project. We follow a strict 4-layer architecture to ensure maintainability, scalability, and clean code.

## 1. Core Architecture Layers

| Layer | Responsibility | Location |
| :--- | :--- | :--- |
| **Model** | Database Schema definition (SQLAlchemy) | `app/models/*.py` |
| **Schema** | Data Validation & Swagger Documentation (Pydantic) | `app/schemas/*.py` |
| **Service** | Pure Business Logic & Database operations | `app/services/*.py` |
| **Endpoint** | Routing, Auth, Rate-limiting & Response Handling | `app/api/endpoints/*.py` |

---

## 2. Step-by-Step implementation

### Step 1: Define the Database Model (`app/models`)
Define your table structure. Use UUIDs for primary keys and include `created_at`/`updated_at`.
```python
class MyFeature(RagBase):
    __tablename__ = "my_features"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    # ... other fields
```

### Step 2: Create Pydantic Schemas (`app/schemas`)
Create separate schemas for **Request (Create/Update)** and **Response**. Use `model_config = ConfigDict(from_attributes=True)` to support SQLAlchemy objects.
- **Documentation**: Use `Field(..., description="...", examples=[...])` for rich Swagger docs.
- **Reference**: [app/schemas/document.py](file:///d:/Dev/Python/rag/app/schemas/document.py)

### Step 3: Implement the Service (`app/services`)
Services should be `@staticmethod` collections. They handle the "heavy lifting."
- **Rule**: Never return FastAPI-specific objects (like `Response` or `HTTPException` if possible) from services; handle logic and return data/dicts.
- **Exception handling**: Raise `HTTPException` only for business domain errors (e.g., "File already exists").
- **Reference**: [app/services/document_service.py](file:///d:/Dev/Python/rag/app/services/document_service.py)

### Step 4: Create the Router/Endpoint (`app/api/endpoints`)
The "Controller" layer.
- **Interceptors**: Use the `APIResponse.success()` or `APIResponse.error()` for uniform JSON output.
- **Security**: Apply `Depends(RequireAdmin)` or `RequireAdminOrUser` for permission control.
- **Tags**: Use `tags=["My Category"]` for grouping in Swagger.
- **Reference**: [app/api/endpoints/documents.py](file:///d:/Dev/Python/rag/app/api/endpoints/documents.py)

---

## 3. Best Practices & Standard Patterns

### Paging Standard
When returning lists, ALWAYS use the `items` + `pagination` object format:
```json
{
  "items": [...],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "limit": 10,
    "total_records": 48
  }
}
```

### Standard API Response Wrapper
All endpoints must return via `APIResponse.success()` to ensure this structure:
```json
{
  "success": true,
  "message": "Action successful",
  "data": { ... },
  "status_code": 200
}
```

### Naming Conventions
- **Folders/Files**: Snake case (`document_service.py`).
- **Classes**: Pascal case (`DocumentService`).
- **Endpoints**: Kebab case (`/upload-document`).

## 4. Swagger Verification
After implementation, always verify at: `http://localhost:2603/docs`
Check if:
1. Descriptions are clear.
2. Examples are helpful.
3. Response types are correctly typed in Pydantic.
