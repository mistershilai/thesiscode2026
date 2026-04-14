"""Authentication API routes."""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from ..core.auth import authenticate, create_token, verify_token, add_user, list_users, delete_user

auth_router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


class AddUserRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role: str = "user"


def get_current_user(request: Request) -> dict:
    """Dependency: extract and verify JWT from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = auth_header[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return payload


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return user


@auth_router.post("/login")
def login(req: LoginRequest):
    user = authenticate(req.username, req.password)
    if not user:
        raise HTTPException(401, "Invalid username or password")
    token = create_token(user)
    return {"token": token, "user": user}


@auth_router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


@auth_router.get("/users")
def get_users(user: dict = Depends(require_admin)):
    return list_users()


@auth_router.post("/users/add")
def create_user(req: AddUserRequest, user: dict = Depends(require_admin)):
    if not add_user(req.username, req.password, req.full_name, req.role):
        raise HTTPException(400, f"Username '{req.username}' already exists")
    return {"status": "ok", "username": req.username}


@auth_router.post("/users/delete")
def remove_user(body: dict, user: dict = Depends(require_admin)):
    username = body.get("username", "").strip()
    if not username:
        raise HTTPException(400, "username is required")
    if username == user.get("sub"):
        raise HTTPException(400, "Cannot delete your own account")
    try:
        if not delete_user(username):
            raise HTTPException(404, f"User '{username}' not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok", "deleted": username}
