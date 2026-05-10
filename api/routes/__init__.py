from fastapi import APIRouter

from .process import router as process_router
from .status import router as status_router
from .health import router as health_router
from .payments import router as payments_router
from .match import router as match_router
from .analyze import router as analyze_router
from .upload import router as upload_router
from .scrape import router as scrape_router 

router = APIRouter()

router.include_router(process_router)
router.include_router(status_router)
router.include_router(health_router)
router.include_router(payments_router)
router.include_router(match_router)
router.include_router(analyze_router)
router.include_router(upload_router)
router.include_router(scrape_router)