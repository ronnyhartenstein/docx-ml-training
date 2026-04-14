from fastapi import APIRouter
from fastapi.responses import JSONResponse

import httpx

from config import settings

router = APIRouter()


@router.get("/health")
async def health():
    # MLX-Server prüfen
    mlx_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.mlx_server_url}/v1/models")
            mlx_ok = resp.status_code == 200
    except Exception:
        pass

    status = "ok" if mlx_ok else "degraded"
    return JSONResponse(
        {"status": status, "mlx_server": mlx_ok},
        status_code=200 if mlx_ok else 503,
    )
