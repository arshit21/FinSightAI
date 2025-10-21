import os
from dotenv import load_dotenv
load_dotenv()

import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

PROJECT_URL = os.getenv("SUPABASE_URL")
if not PROJECT_URL:
    raise RuntimeError("SUPABASE_URL is required")

JWKS_URL = f"{PROJECT_URL}/auth/v1/.well-known/jwks.json"
AUD = "authenticated"
ALGS = ["ES256"]

_jwk_client = PyJWKClient(JWKS_URL)

class JWTBearer(HTTPBearer):
    async def __call__(self, request: Request):
        cred: HTTPAuthorizationCredentials = await super().__call__(request)
        if not cred or cred.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
        token = cred.credentials
        try:
            signing_key = _jwk_client.get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=ALGS,
                audience=AUD,
                options={"require": ["exp", "iat"]},
            )
            request.state.user = payload
            return token
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")