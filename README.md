# Tender Engine API

AI-powered tender intelligence and automation platform built with FastAPI, Selenium, PDF extraction, and asynchronous background scraping.

---

# Overview

Tender Engine API automates the process of:

* discovering government tenders
* scraping tender listings
* downloading tender PDFs
* organizing tender documents
* processing tender data asynchronously
* exposing results through a FastAPI backend
* presenting results through a modern frontend dashboard

The platform is designed to reduce manual tender monitoring and document processing time.

---

# Core Features

## Tender Scraping

* Automated Selenium-based tender scraping
* Dynamic page rendering support
* AJAX-aware extraction logic
* Pagination support
* Relevant tender filtering

---

## PDF Downloads

* Automatic tender PDF downloads
* Organized download storage
* ZIP archive export support

---

## Asynchronous Job System

* Background scraping workers
* Non-blocking FastAPI architecture
* Job status tracking
* Result polling endpoints

---

## Modern Frontend Dashboard

* Responsive UI
* Tender dashboard view
* Download actions
* Scrape progress indicators
* Result display system

---

# Technology Stack

## Backend

* Python 3.12+
* FastAPI
* Uvicorn
* Selenium
* webdriver-manager
* Pandas

---

## Frontend

* HTML
* CSS
* Vanilla JavaScript

---

## Automation

* Selenium ChromeDriver
* Asynchronous background workers

---

# Project Structure

```text
project-root/
│
├── api/
│   ├── main.py
│   ├── routes/
│   │   ├── scrape.py
│   │   ├── process.py
│   │   ├── upload.py
│   │   └── __init__.py
│   │
│   └── services/
│       ├── scraper.py
│       ├── worker.py
│       └── ...
│
├── static/
│   └── index.html
│
├── downloads/
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Installation

## 1. Clone Repository

```bash
git clone https://github.com/alljaybly/tender-engine-api.git
cd tender-engine-api
```

---

## 2. Create Virtual Environment

### Ubuntu / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Required Dependencies

Main packages include:

```text
fastapi
uvicorn
selenium
webdriver-manager
pandas
python-multipart
requests
```

---

# Chrome / Selenium Requirements

Google Chrome must be installed.

ChromeDriver is automatically managed using:

```python
webdriver-manager
```

No manual driver installation is normally required.

---

# Running the Application

## Start FastAPI Server

```bash
uvicorn api.main:app --reload
```

Expected output:

```text
Application startup complete
```

---

# Accessing the System

## Frontend Dashboard

```text
http://127.0.0.1:8000
```

---

## FastAPI Swagger Docs

```text
http://127.0.0.1:8000/docs
```

---

# Scraping Workflow

## Step 1

User clicks:

```text
Start Scrape
```

---

## Step 2

FastAPI immediately returns:

```json
{
  "status": "queued",
  "job_id": "example-job-id"
}
```

---

## Step 3

Background worker launches Selenium scraper.

---

## Step 4

Frontend polls:

```text
/api/results/{job_id}
```

until results are complete.

---

## Step 5

Tender results appear in dashboard.

---

## Step 6

User downloads:

* PDFs
* ZIP archive

---

# API Endpoints

## Start Scrape

```http
GET /api/scrape
```

Response:

```json
{
  "status": "queued",
  "job_id": "123"
}
```

---

## Get Results

```http
GET /api/results/{job_id}
```

Possible responses:

### Processing

```json
{
  "status": "processing"
}
```

### Complete

```json
{
  "status": "complete",
  "tenders": []
}
```

### Failed

```json
{
  "status": "failed",
  "error": "details"
}
```

---

# Downloads

Downloaded PDFs are stored in:

```text
/downloads
```

ZIP exports package downloaded tender documents into a single archive.

---

# Logging

The scraper includes detailed logging for:

* browser startup
* navigation
* page processing
* table detection
* tender extraction
* download status
* job completion
* failure handling

---

# Common Issues

## ChromeDriver Errors

### Problem

```text
ChromeDriver version mismatch
```

### Fix

Update Chrome browser.

Delete cached drivers if needed:

```bash
rm -rf .wdm/
```

---

## Empty Tender Results

### Possible Causes

* website structure changed
* selectors outdated
* AJAX rendering delay

### Fix

Inspect live DOM and update Selenium selectors.

---

## Selenium Timeout

### Problem

```text
ReadTimeoutError
```

### Fix

* verify internet connection
* verify eTenders site accessibility
* ensure waits target populated table content

---

# Development Notes

## Architecture

The system uses:

* asynchronous FastAPI routes
* background worker execution
* Selenium isolation from API thread

This prevents the FastAPI server from freezing during long scraping jobs.

---

# Git Workflow

## Save Changes

```bash
git add .
git commit -m "Describe changes"
git push
```

---

## Create Stable Version Tag

```bash
git tag stable-v1
git push origin stable-v1
```

---

# Recommended Future Improvements

## Backend

* Redis queue system
* Celery workers
* PostgreSQL integration
* authentication system
* user accounts
* role permissions

---

## Frontend

* charts and analytics
* advanced filtering
* export dashboards
* notifications
* multi-user collaboration

---

## AI Features

* tender summarization
* bid scoring
* recommendation engine
* opportunity prioritization
* AI-generated compliance checks

---

# Security Notes

Before production deployment:

* secure API endpoints
* add authentication
* validate uploads
* limit scraping concurrency
* protect sensitive files
* configure HTTPS

---

# Deployment Notes

Current setup is suitable for:

* development
* internal testing
* pilot customers

Recommended production stack:

* Nginx
* Gunicorn/Uvicorn workers
* Redis
* PostgreSQL
* Docker
* cloud VM/container deployment

---

# License

Specify your preferred license before public commercial release.

Recommended:

* Proprietary commercial license
  OR
* MIT License (if open source)

---

# Contact

Project Owner:

Allan Blythe

GitHub Repository:

[https://github.com/alljaybly/tender-engine-api](https://github.com/alljaybly/tender-engine-api)

---

# Final Notes

Tender Engine API is designed as a scalable procurement intelligence platform capable of evolving into a full enterprise tender automation solution.

The current version provides:

* asynchronous scraping
* automated document acquisition
* centralized tender monitoring
* modern UI dashboard
* extensible FastAPI architecture

This creates a strong foundation for enterprise procurement automation and AI-assisted tender operations.
