# AI-Powered Transaction Processing Pipeline

## Overview

This project is a backend system for processing financial transaction CSV files asynchronously using FastAPI, Celery, Redis, PostgreSQL, and Google's Gemini LLM.

The system accepts uploaded transaction files, cleans and normalizes the data, detects anomalies, classifies uncategorized transactions using an LLM, generates spending insights, and exposes the results through REST APIs.

---

## Tech Stack

### Backend

* FastAPI

### Database

* PostgreSQL

### Queue System

* Celery
* Redis

### LLM

* Google Gemini

### Containerization

* Docker
* Docker Compose

---

## System Architecture

User
↓
FastAPI API
↓
PostgreSQL (Job Record)
↓
Celery Task Queue
↓
Redis Broker
↓
Celery Worker
↓
Data Cleaning
↓
Anomaly Detection
↓
Gemini Classification
↓
Gemini Summary Generation
↓
PostgreSQL Storage
↓
Results API

---

## Features

### CSV Upload

Upload transaction CSV files asynchronously.

### Data Cleaning

* Remove duplicate rows
* Normalize dates to ISO format
* Uppercase status values
* Normalize currency values
* Remove currency symbols
* Fill missing categories with "Uncategorised"

### Anomaly Detection

Flag transactions when:

1. Amount exceeds 3× account median
2. Currency is USD while merchant is a domestic-only brand:

   * Swiggy
   * Ola
   * IRCTC

Multiple anomaly reasons are supported.

### LLM Transaction Classification

Transactions with missing categories are classified into:

* Food
* Shopping
* Travel
* Transport
* Utilities
* Cash Withdrawal
* Entertainment
* Other

Classification is performed in batches.

### LLM Spending Summary

Generates:

* Total INR spend
* Total USD spend
* Top 3 merchants
* Anomaly count
* Spending narrative
* Risk level

### Retry Logic

Failed LLM requests:

* Retry up to 3 times
* Exponential backoff
* Mark as llm_failed if all retries fail

---

## API Endpoints

### Upload CSV

POST /jobs/upload

Upload a transaction CSV file.

Response:

{
"job_id": 1,
"status": "pending"
}

---

### Job Status

GET /jobs/{job_id}/status

Response:

{
"job_id": 1,
"status": "completed",
"summary": {
"total_spend_inr": 1339923,
"total_spend_usd": 74185.14,
"anomaly_count": 5,
"risk_level": "medium"
}
}

---

### Job Results

GET /jobs/{job_id}/results

Returns:

* Processed transactions
* Category breakdown
* Anomalies
* Narrative summary

---

### List Jobs

GET /jobs

Optional:

GET /jobs?status=completed

---

## Database Schema

### Job

* id
* filename
* status
* row_count_raw
* row_count_clean
* created_at
* completed_at
* processed_filename
* error_message

### Transaction

* txn_id
* date
* merchant
* amount
* currency
* status
* category
* account_id
* is_anomaly
* anomaly_reason
* llm_category
* llm_raw_response
* llm_failed

### JobSummary

* total_spend_inr
* total_spend_usd
* top_merchants
* anomaly_count
* narrative
* risk_level

---

## Gemini Prompts

### Transaction Classification Prompt

You are a finance classifier.

For each transaction assign ONE category:

Food
Shopping
Travel
Transport
Utilities
Cash Withdrawal
Entertainment
Other

Return ONLY JSON.

---

### Summary Prompt

Generate JSON only.

Return:

{
"total_spend_inr": number,
"total_spend_usd": number,
"top_merchants": [],
"anomaly_count": number,
"narrative": "",
"risk_level": "low|medium|high"
}

---

## Running the Project

### Clone Repository

git clone <repository_url>

cd transaction-pipeline

---

### Create Environment File

Create .env

DATABASE_URL=postgresql://postgres:postgres@postgres:5432/transactions_db

REDIS_URL=redis://redis:6379/0

GEMINI_API_KEY=YOUR_API_KEY

---

### Start Application

docker compose up --build

---

## Service URLs

FastAPI:

http://localhost:8000

Swagger:

http://localhost:8000/docs

ReDoc:

http://localhost:8000/redoc

---

## Example cURL Commands

### Upload CSV

curl -X POST 
-F "file=@transactions.csv" 
http://localhost:8000/jobs/upload

### Job Status

curl http://localhost:8000/jobs/1/status

### Job Results

curl http://localhost:8000/jobs/1/results

### List Jobs

curl http://localhost:8000/jobs

---

## Future Improvements

* JWT Authentication
* Pagination
* Foreign Key Constraints
* WebSocket Progress Updates
* Dashboard UI
* Multi-file Processing
* Advanced Fraud Detection Rules
* Kubernetes Deployment
