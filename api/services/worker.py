import asyncio
import logging

from .job_store import get_job, update_job

logger = logging.getLogger(__name__)


async def process_job(job_id: str, filename: str, cost_per_hour: float):
    logger.info(f"[JOB] job_id=%s status=processing", job_id)
    
    update_job(job_id, status="processing")
    
    try:
        steps = ["extraction", "validation", "pricing"]
        for step in steps:
            logger.info(f"[STEP] {step}")
            update_job(job_id, progress=step)
            await asyncio.sleep(0.5)
        
        update_job(
            job_id,
            status="complete",
            result={
                "summary": "Processed successfully",
                "price_estimate": cost_per_hour * 10
            }
        )
        logger.info(f"[JOB] job_id=%s status=complete", job_id)
    except Exception as e:
        update_job(job_id, status="failed", error=str(e))
        logger.info(f"[JOB] job_id=%s status=failed", job_id)
