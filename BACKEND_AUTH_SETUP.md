# Backend Auth0 JWT Verification Setup

## 📦 Install Dependencies

For your FastAPI backend, install these packages:

```bash
pip install python-jose[cryptography] python-multipart
```

Or add to your `requirements.txt`:
```
python-jose[cryptography]
python-multipart
```

---

## 🔧 Create Auth Middleware

Create a file: `app/middleware/auth.py`

```python
from functools import wraps
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests
from datetime import datetime

# Auth0 Configuration
AUTH0_DOMAIN = "dev-gaytaln1ju54r4wq.us.auth0.com"
AUTH0_AUDIENCE = "https://api.cognitoforge.com"
ALGORITHMS = ["RS256"]

# HTTP Bearer token scheme
security = HTTPBearer()

class Auth0JWKSClient:
    """Client to fetch and cache Auth0 JWKS (JSON Web Key Set)"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.jwks_uri = f"https://{domain}/.well-known/jwks.json"
        self._jwks = None
        self._last_fetch = None
    
    def get_jwks(self):
        """Fetch JWKS from Auth0 (cached for 24 hours)"""
        if self._jwks and self._last_fetch:
            # Cache for 24 hours
            if (datetime.now() - self._last_fetch).total_seconds() < 86400:
                return self._jwks
        
        response = requests.get(self.jwks_uri)
        response.raise_for_status()
        self._jwks = response.json()
        self._last_fetch = datetime.now()
        return self._jwks
    
    def get_signing_key(self, token: str):
        """Get the signing key for token verification"""
        jwks = self.get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Unable to find appropriate key")
        
        return rsa_key

# Initialize JWKS client
jwks_client = Auth0JWKSClient(AUTH0_DOMAIN)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verify Auth0 JWT token and return decoded payload
    
    Usage in FastAPI endpoints:
        @app.get("/protected")
        async def protected_route(token_payload: dict = Depends(verify_token)):
            user_id = token_payload.get("sub")
            return {"message": "Success", "user_id": user_id}
    """
    token = credentials.credentials
    
    try:
        # Get the signing key
        signing_key = jwks_client.get_signing_key(token)
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication credentials: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: {str(e)}"
        )

def optional_verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
) -> Optional[dict]:
    """
    Optional token verification - allows both authenticated and unauthenticated access
    
    Usage:
        @app.get("/optional-auth")
        async def route(token_payload: Optional[dict] = Depends(optional_verify_token)):
            if token_payload:
                user_id = token_payload.get("sub")
                return {"authenticated": True, "user_id": user_id}
            return {"authenticated": False}
    """
    if credentials is None:
        return None
    
    return verify_token(credentials)

def require_permission(permission: str):
    """
    Decorator to require specific permission from Auth0 token
    
    Usage:
        @app.get("/admin")
        async def admin_route(token: dict = Depends(require_permission("admin:access"))):
            return {"message": "Admin access granted"}
    """
    def permission_checker(token_payload: dict = Depends(verify_token)) -> dict:
        permissions = token_payload.get("permissions", [])
        
        if permission not in permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Required permission: {permission}"
            )
        
        return token_payload
    
    return permission_checker

# Helper function to get user info from token
def get_user_id(token_payload: dict = Depends(verify_token)) -> str:
    """Extract user ID from token payload"""
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    return user_id

def get_user_email(token_payload: dict = Depends(verify_token)) -> str:
    """Extract user email from token payload"""
    email = token_payload.get("email") or token_payload.get("https://api.cognitoforge.com/email")
    if not email:
        raise HTTPException(status_code=401, detail="Email not found in token")
    return email
```

---

## 🚀 Usage in FastAPI Routes

### Update your `main.py`:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import verify_token, optional_verify_token, get_user_id

app = FastAPI(title="CognitoForge API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public endpoint (no auth required)
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

# Protected endpoint (auth required)
@app.post("/api/upload")
async def upload_repository(
    repo_url: str,
    analysis_type: str,
    user_id: str = Depends(get_user_id)
):
    """Upload repository - requires authentication"""
    return {
        "message": "Repository uploaded successfully",
        "user_id": user_id,
        "repo_url": repo_url
    }

# Protected endpoint with full token access
@app.post("/api/simulate")
async def simulate_attack(
    repo_id: str,
    token_payload: dict = Depends(verify_token)
):
    """Simulate attack - requires authentication"""
    user_id = token_payload.get("sub")
    user_email = token_payload.get("email")
    
    return {
        "message": "Simulation started",
        "user_id": user_id,
        "user_email": user_email,
        "repo_id": repo_id
    }

# Optional auth endpoint
@app.get("/api/reports/latest")
async def get_latest_report(
    token_payload: dict = Depends(optional_verify_token)
):
    """Get latest report - auth optional"""
    if token_payload:
        user_id = token_payload.get("sub")
        return {"message": "User-specific reports", "user_id": user_id}
    return {"message": "Public reports"}
```

---

## 🔐 Environment Variables

Create `.env` file in backend directory:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=dev-gaytaln1ju54r4wq.us.auth0.com
AUTH0_AUDIENCE=https://api.cognitoforge.com

# API Configuration
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
```

Update your auth middleware to use environment variables:

```python
import os
from dotenv import load_dotenv

load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "dev-gaytaln1ju54r4wq.us.auth0.com")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.cognitoforge.com")
```

---

## 🧪 Testing the Auth

### Test with curl:

```bash
# Get a token from Auth0 first (from frontend login)
# Then test protected endpoint:

curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/test/repo", "analysis_type": "comprehensive"}'
```

### Test without token (should fail):

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/test/repo", "analysis_type": "comprehensive"}'

# Expected: 401 Unauthorized
```

---

## 📋 Integration Checklist

- [ ] Install `python-jose[cryptography]` and `python-multipart`
- [ ] Create `app/middleware/auth.py` with the code above
- [ ] Update environment variables in `.env`
- [ ] Add `from app.middleware.auth import verify_token` to your routes
- [ ] Protect endpoints with `Depends(verify_token)`
- [ ] Update CORS origins to include your frontend URL
- [ ] Test with real Auth0 tokens from frontend
- [ ] Handle token errors gracefully

---

## 🐛 Troubleshooting

**Error: "Unable to find appropriate key"**
- Solution: Check that AUTH0_DOMAIN is correct
- Verify token is not expired
- Ensure JWKS endpoint is accessible

**Error: "Invalid audience"**
- Solution: Verify AUTH0_AUDIENCE matches your Auth0 API identifier
- Check that frontend is requesting tokens with correct audience

**Error: "Token expired"**
- Solution: Frontend should automatically refresh tokens
- Check token expiration settings in Auth0 dashboard

---

## 🚀 Next Steps

1. Switch to backend branch: `git checkout backend`
2. Create the middleware file
3. Install dependencies
4. Update your routes to use `Depends(verify_token)`
5. Test with frontend authentication
6. Deploy with environment variables configured

**The frontend is already configured to send tokens automatically!**
