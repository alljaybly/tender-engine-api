from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from typing import Optional
from fastapi.responses import JSONResponse
import uuid
import asyncio
import logging
from pathlib import Path

from ..utils import error_response

from ..services.job_store import create_job, update_job
from ..services.worker import process_job
from ..services.user_store import record_job_failure

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path(__file__).resolve().parents[2] / 'storage' / 'uploads'
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post('/process-tender')
async def process_tender(request: Request, file: UploadFile = File(...), cost_per_hour: Optional[float] = Form(None)):
    if cost_per_hour is not None and cost_per_hour <= 0:
        return error_response("validation_error", "cost_per_hour must be greater than 0", 422)
    
    job_id = uuid.uuid4().hex
    user = getattr(request.state, 'user', {})
    logger.info("[PROCESS] Received file for job %s user=%s filename=%s", job_id, user.get('user_id'), file.filename)

    # save file
    suffix = Path(file.filename).suffix or ''
    out_path = STORAGE_DIR / f"{job_id}{suffix}"
    try:
        contents = await file.read()
        with open(out_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        logger.exception("[PROCESS] Failed to save uploaded file: %s", e)
        record_job_failure(user.get('api_key'))
        raise HTTPException(status_code=500, detail='Failed to save uploaded file')

    create_job(job_id)
    update_job(
        job_id,
        api_key=user.get('api_key'),
        user={'user_id': user.get('user_id'), 'email': user.get('email')}
    )

    # Use default cost_per_hour if not provided
    final_cost_per_hour = cost_per_hour if cost_per_hour is not None else 100.0

    # Launch background task
    asyncio.create_task(process_job(job_id, str(out_path), final_cost_per_hour))

    return JSONResponse({
        "job_id": job_id,
        "status": "queued"
    })
