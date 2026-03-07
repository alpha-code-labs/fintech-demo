from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import macro, scanner, stock, portfolio, briefing
from app.scheduler import start_scheduler, stop_scheduler, get_scheduler_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Investment Scanner API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(macro.router, prefix="/api")
app.include_router(scanner.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(briefing.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/api/scheduler/status")
def scheduler_status():
    return get_scheduler_status()
