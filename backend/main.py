from fastapi import FastAPI
from auth.supabase_client import supabase

app = FastAPI()

@app.get("/")
def root():
    return{"message": "Hello World"}

@app.get("/health")
def health():
    try:
        supabase.table("health-meta").select("id").limit(1).execute()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "fail", "error": str(e)}