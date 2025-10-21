from fastapi import FastAPI, Depends
from auth.routes import router as auth_router
from auth.jwt_guard import JWTBearer

app = FastAPI()

app.include_router(auth_router)

@app.get("/")
def root():
    return{"message": "Hello World"}

@app.get("/protected", dependencies=[Depends(JWTBearer())], tags=["test"])
def protected():
    return {"ok": True}