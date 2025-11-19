import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User as UserSchema, Like as LikeSchema, Match as MatchSchema, Message as MessageSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def to_str_id(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    # Convert nested ObjectIds if any
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


@app.get("/")
def read_root():
    return {"message": "Dating API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Schemas for requests
class CreateUser(BaseModel):
    name: str
    gender: str
    seeking: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


@app.post("/api/users", response_model=dict)
def create_user(payload: CreateUser):
    data = UserSchema(**payload.model_dump())
    user_id = create_document("user", data)
    doc = db["user"].find_one({"_id": ObjectId(user_id)})
    return to_str_id(doc)


@app.get("/api/users", response_model=List[dict])
def list_users():
    docs = get_documents("user")
    return [to_str_id(d) for d in docs]


class LikePayload(BaseModel):
    liker_id: str
    liked_id: str


@app.post("/api/likes", response_model=dict)
def like_user(payload: LikePayload):
    if payload.liker_id == payload.liked_id:
        raise HTTPException(status_code=400, detail="Cannot like yourself")
    # Create like
    like = LikeSchema(**payload.model_dump())
    like_id = create_document("like", like)

    # Check for reciprocal like to form a match
    reciprocal = db["like"].find_one({
        "liker_id": payload.liked_id,
        "liked_id": payload.liker_id
    })
    match_doc = None
    if reciprocal:
        # Create match if not already exists
        existing = db["match"].find_one({
            "$or": [
                {"user1_id": payload.liker_id, "user2_id": payload.liked_id},
                {"user1_id": payload.liked_id, "user2_id": payload.liker_id}
            ]
        })
        if not existing:
            # Core idea: both can make the first move if allow_both_first_move is True
            match = MatchSchema(user1_id=payload.liker_id, user2_id=payload.liked_id, allow_both_first_move=True)
            match_id = create_document("match", match)
            match_doc = db["match"].find_one({"_id": ObjectId(match_id)})
        else:
            match_doc = existing

    like_doc = db["like"].find_one({"_id": ObjectId(like_id)})
    result = {"like": to_str_id(like_doc)}
    if match_doc:
        result["match"] = to_str_id(match_doc)
    return result


@app.get("/api/matches/{user_id}", response_model=List[dict])
def get_matches(user_id: str):
    matches = db["match"].find({
        "$or": [
            {"user1_id": user_id},
            {"user2_id": user_id}
        ]
    })
    return [to_str_id(m) for m in matches]


class MessagePayload(BaseModel):
    match_id: str
    sender_id: str
    text: str


@app.post("/api/messages", response_model=dict)
def send_message(payload: MessagePayload):
    # Check match exists
    match = db["match"].find_one({"_id": ObjectId(payload.match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    # Check sender is part of match
    if payload.sender_id not in [match["user1_id"], match["user2_id"]]:
        raise HTTPException(status_code=403, detail="Not part of this match")

    # Key feature: if allow_both_first_move True, allow anyone to send first.
    # Otherwise, you could enforce gender rules; here we default to both allowed.
    message = MessageSchema(**payload.model_dump())
    msg_id = create_document("message", message)
    doc = db["message"].find_one({"_id": ObjectId(msg_id)})
    return to_str_id(doc)


@app.get("/api/messages/{match_id}", response_model=List[dict])
def list_messages(match_id: str):
    msgs = db["message"].find({"match_id": match_id}).sort("created_at", 1)
    return [to_str_id(m) for m in msgs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
