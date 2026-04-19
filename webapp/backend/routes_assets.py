from fastapi import APIRouter, Query
from webapp.backend.assets import ASSET_PRESETS, search_assets

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/presets")
def get_presets():
    return ASSET_PRESETS


@router.get("/search")
def search(q: str = Query("")):
    return search_assets(q)
