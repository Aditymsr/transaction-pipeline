from fastapi import FastAPI

from app.database.database import Base, engine
import app.models.job

from app.api.jobs import router as jobs_router

app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.include_router(jobs_router)

@app.get("/")
def root():
    return {"message": "running"}