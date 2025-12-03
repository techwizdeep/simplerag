import base64
import json
from typing import Optional
from fastapi import Request, HTTPException

def get_client_principal(request: Request) -> Optional[dict]:
    """
    Reads X-MS-CLIENT-PRINCIPAL (Easy Auth) header and returns the decoded JSON.
    Returns None if user isn't authenticated.
    """
    header = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not header:
        return None

    try:
        decoded = base64.b64decode(header)
        data = json.loads(decoded.decode("utf-8"))
        return data
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid client principal header")


def get_current_user(request: Request) -> dict:
    """
    Convenience function: raises 401 if not authenticated.
    """
    principal = get_client_principal(request)
    if not principal:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # typical claim with the user name/email is "name" or "preferred_username"
    claims = principal.get("claims", [])
    user_dict = {"user_id": None, "name": None, "email": None}

    for c in claims:
        typ = c.get("typ")
        val = c.get("val")
        if typ.endswith("/name") and not user_dict["name"]:
            user_dict["name"] = val
        if "email" in typ or "preferred_username" in typ:
            user_dict["email"] = val
        if typ.endswith("/objectidentifier") or typ.endswith("/nameidentifier"):
            user_dict["user_id"] = val

    return user_dict
