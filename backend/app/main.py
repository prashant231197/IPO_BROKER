import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as legacy_router
from .api.companies import router as companies_router
from .api.documents import router as documents_router
from .api.research import router as research_router
from .api.scoring import router as scoring_router
from .config import CORS_ORIGINS
from .db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="IPO Radar — Evidence-Based Indian IPO Research Platform",
    description="Multi-source Evidence-Based Research & Scoring Intelligence for Indian IPOs. "
                "Research & education only — not investment advice.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(legacy_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(scoring_router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    init_db()
