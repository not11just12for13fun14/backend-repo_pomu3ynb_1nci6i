import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for requests
class FurnitureCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    material: Optional[str] = None
    dimensions: Optional[str] = None
    price: float
    stock: int = 0
    image_url: Optional[str] = None
    is_featured: bool = False

class FurnitureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    is_featured: Optional[bool] = None

@app.get("/")
def read_root():
    return {"message": "Furniture API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# Furniture endpoints using MongoDB helpers
@app.post("/api/furniture")
def create_furniture(item: FurnitureCreate):
    from database import create_document
    try:
        inserted_id = create_document("furniture", item)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/furniture")
def list_furniture(q: Optional[str] = None, category: Optional[str] = None, featured: Optional[bool] = None, limit: int = 50):
    from database import get_documents
    try:
        filter_dict = {}
        if category:
            filter_dict["category"] = category
        if featured is not None:
            filter_dict["is_featured"] = featured
        # Basic text search across name/description (simple contains)
        docs = get_documents("furniture", filter_dict, limit)
        if q:
            q_lower = q.lower()
            docs = [d for d in docs if q_lower in (d.get("name", "").lower() + " " + (d.get("description", "") or "").lower())]
        # Convert ObjectId
        for d in docs:
            if isinstance(d.get("_id"), ObjectId):
                d["id"] = str(d.pop("_id"))
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/furniture/{item_id}")
def update_furniture(item_id: str, payload: FurnitureUpdate):
    from database import db
    try:
        update_doc = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_doc:
            return {"updated": False}
        update_doc["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        result = db["furniture"].update_one({"_id": ObjectId(item_id)}, {"$set": update_doc})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"updated": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/furniture/{item_id}")
def delete_furniture(item_id: str):
    from database import db
    try:
        result = db["furniture"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
