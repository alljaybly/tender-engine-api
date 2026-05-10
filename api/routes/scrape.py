from fastapi import APIRouter
from api.services.scraper import scrape_tenders

router = APIRouter()

@router.get("/scrape")
def scrape():
    tenders = scrape_tenders() or []

    return {
        "status": "success",
        "total": len(tenders),
        "tenders": tenders
    }