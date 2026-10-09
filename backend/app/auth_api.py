from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Flat, Tower, User
from app.security import JWT_TTL_SECONDS, create_access_token, current_user, hash_password, verify_password
from fastapi import Depends

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)

class PasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

@router.post("/login")
def login(inputs: LoginInput):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == inputs.email.lower().strip()))
        if user is None or not user.is_active or not verify_password(inputs.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email or password is incorrect")
        token = create_access_token(user)
        flat = session.get(Flat, user.flat_id) if user.flat_id else None
        tower = session.get(Tower, flat.tower_id) if flat else None
        return {"access_token": token, "token_type": "bearer", "expires_in": JWT_TTL_SECONDS, "user": {"id": user.id, "email": user.email, "role": user.role, "flat_id": user.flat_id, "flat_number": flat.flat_number if flat else None, "tower": tower.name if tower else None}}

@router.get("/me")
def me(user: User = Depends(current_user)):
    with SessionLocal() as session:
        flat = session.get(Flat, user.flat_id) if user.flat_id else None
        tower = session.get(Tower, flat.tower_id) if flat else None
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "flat_id": user.flat_id,
            "flat_number": flat.flat_number if flat else None,
            "tower": tower.name if tower else None,
        }

@router.patch("/password")
def change_password(inputs: PasswordChangeInput, user: User = Depends(current_user)):
    if inputs.current_password == inputs.new_password:
        raise HTTPException(status_code=400, detail="Choose a different password")
    with SessionLocal.begin() as session:
        record = session.get(User, user.id)
        if record is None or not verify_password(inputs.current_password, record.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        record.password_hash = hash_password(inputs.new_password)
    return {"changed": True}
