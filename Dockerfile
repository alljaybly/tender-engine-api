# ============================================================
# STAGE 1: Builder
#   Installs all Python dependencies into a virtual environment.
#   Keeps build tools like gcc in this ephemeral stage so the final
#   image stays lean. After pip install completes, only the virtual
#   environment (/opt/venv) is copied to the runtime stage, and this
#   entire builder layer is discarded.
# ============================================================
FROM python:3.12-slim AS builder

# Prevent Python bytecode .pyc files and disable stdout buffering
# for cleaner logs and immediate output in container environments.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system build dependencies required for compiling
# native Python wheels (numpy, scipy, torch C-extensions, etc.).
# These are NOT needed at runtime — only at pip-install time.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment so the runtime stage
# can simply copy /opt/venv without relying on system site-packages.
RUN python -m venv /opt/venv
# Activate the venv for all subsequent RUN commands in this stage.
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements FIRST to maximise Docker layer caching.
# As long as requirements.txt does not change, the expensive
# pip install layer is served from cache.
COPY requirements.txt .

# Upgrade pip for best dependency resolution, then install
# all Python dependencies inside the virtual environment.
# --no-cache-dir avoids bloating the layer with pip cache files.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# STAGE 2: Final runtime image
#   Minimal Debian-slim image with only the essential system
#   packages needed by the OCR pipeline at runtime. The virtual
#   environment (with all Python packages) is copied from builder.
# ============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install system-level OCR and PDF-rendering dependencies.
# tesseract-ocr   : OCR engine used by pytesseract.
# poppler-utils   : pdftoppm/pdfinfo for PDF-to-image conversion.
# ghostscript     : PostScript/PDF interpreter used by pdf2image.
# --no-install-recommends prevents pulling unnecessary packages.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        ghostscript \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the fully-populated virtual environment from builder.
# This includes ALL Python packages without re-running pip.
COPY --from=builder /opt/venv /opt/venv

# Use /app as the container working directory.
WORKDIR /app

# Copy the application source code last. Since source changes
# frequently, placing COPY . . last keeps earlier layers cached.
COPY . .

# Create a dedicated non-root user for production security.
# The appuser owns /app (and /opt/venv) so the process can
# write temporary files (uploads, PDF rendering, etc.) safely.
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -d /app -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app /opt/venv
USER appuser

# Declare the port the application listens on.
# This is documentation only; actual port mapping happens at runtime.
EXPOSE 8000

# Health check for container orchestrators (Docker, K8s, ECS, etc.).
# Polls the API health endpoint every 30s. The 15s start-period
# gives the application time to initialise before failures count.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; u=urllib.request.urlopen('http://localhost:8000/api/health'); assert u.status == 200, u.status" || exit 1

# Start uvicorn with the FastAPI app.
# exec-form CMD (JSON array) ensures proper SIGTERM signal handling.
# --workers 1: scale horizontally via container replicas instead.
# --timeout-keep-alive 5: recycle stale HTTP keep-alive connections.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "5"]

