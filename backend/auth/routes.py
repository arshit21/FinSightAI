from fastapi import APIRouter, HTTPException
from .supabase_client import supabase

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(payload: dict):
    res = supabase.auth.sign_in_with_password({"email": payload["email"], "password": payload["password"]})
    if not getattr(res, "session", None) or getattr(res, "error", None):
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    return {"access_token": res.session.access_token, "token_type": "bearer"}

@router.post("/logout")
def logout():
    err = supabase.auth.sign_out()
    if err:
        raise HTTPException(status_code=400, detail="Logout Failed")
    return {"status": "Successfully Logged Out"}

@router.get("/health")
def health():
    try:
        supabase.table("health-meta").select("id").limit(1).execute()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "fail", "error": str(e)}