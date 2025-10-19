from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

import pandas as pd
import numpy as np

import json
import sys
import os
from pathlib import Path

import time

from pyarrow import json as pjson
import pyarrow as pa

import gzip

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager

#import directories
from app.core.config import DATA_DIR, FRONTEND_BUILD_DIR #__init__.py is needed in core to be able to import it

#Cache
from app.utils.helpers import cache, WWWRedirectMiddleware


#----------------------------------------
# Middleware
#----------------------------------------
app = FastAPI()

origins = ['http://localhost','http://localhost:3000','http://127.0.0.1:5173']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(WWWRedirectMiddleware)



#----------------------------------------
# Routes
#----------------------------------------
@app.get("/")
async def root():
    return {"message": "Hello World"}

if os.environ.get('ENV_PROD_OR_DEV') is not None and os.environ.get('ENV_PROD_OR_DEV') == "PROD":
    #this needs to be mounted and added after other routes are defined, otherwise those routes are not accessible
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
    @app.get("/")
    async def serve_frontend(request: Request):
        print("Request headers: ",request.headers)
        print("IP address of the client making the request: ",request.host)
        return FileResponse(os.path.join(FRONTEND_BUILD_DIR, "index.html"))


