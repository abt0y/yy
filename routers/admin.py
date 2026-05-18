from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_account_pool
from core.account_pool import AccountPool
from models.schemas import CookieAddRequest, CookieRecord

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/accounts", response_model=list[CookieRecord])
async def list_accounts(pool: AccountPool = Depends(get_account_pool)) -> list[CookieRecord]:
    return [
        CookieRecord(id=account.id, enabled=account.enabled, fail_count=account.fail_count, proxy=account.proxy)
        for account in pool.list_accounts()
    ]


@router.post("/cookies", response_model=CookieRecord)
async def add_cookie(
    request: CookieAddRequest,
    pool: AccountPool = Depends(get_account_pool),
) -> CookieRecord:
    account = await pool.add_runtime_cookie(
        secure_1psid=request.secure_1psid,
        secure_1psidts=request.secure_1psidts,
        proxy=request.proxy,
        enabled=request.enabled,
        account_id=request.id,
    )
    return CookieRecord(id=account.id, enabled=account.enabled, fail_count=account.fail_count, proxy=account.proxy)


@router.delete("/cookies/{account_id}")
async def delete_cookie(account_id: str, pool: AccountPool = Depends(get_account_pool)) -> dict[str, object]:
    deleted = await pool.remove(account_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return {"id": account_id, "deleted": True}


@router.post("/reload")
async def reload_cookie_files(pool: AccountPool = Depends(get_account_pool)) -> dict[str, object]:
    await pool.load()
    return {"reloaded": True, "accounts": len(pool.list_accounts()), "enabled_accounts": pool.enabled_count()}
