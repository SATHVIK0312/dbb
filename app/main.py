import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import database   # ← FIXED

import routers.users as users
import routers.projects as projects
import routers.testcases as testcases
import routers.executions as executions
import routers.testplans as testplans
import routers.scripts as scripts
import routers.madl_integration as madl_integration
import routers.method_selection as method_selection

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing DB Pool...")
    await database.connect_db()
    print("✅ DB Pool initialized.")

    await madl_integration.initialize_madl()

    yield

    print("🛑 Closing DB Pool...")
    await database.disconnect_db()
    print("✅ DB Closed.")

app = FastAPI(
    title="User Management API",
    description="API to manage users and projects",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8002", "http://127.0.0.1:8002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router, prefix="")
app.include_router(projects.router, prefix="")
app.include_router(testcases.router, prefix="")
app.include_router(executions.router, prefix="")
app.include_router(testplans.router, prefix="")
app.include_router(scripts.router, prefix="")
app.include_router(method_selection.router, prefix="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="debug")
