from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
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

import boto3
from dotenv import load_dotenv
import os
import asyncio
from dateutil import parser

load_dotenv()


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



#----------------------------------------
# Routes
#----------------------------------------
@app.get("/home")
async def root():
    return {"message": "Hello World"}

#@app.get("/api/v1/telemetry")
#async def getTelemetry():
def getTelemetry():
    try: 
        #prod
        dynamodb = boto3.resource('dynamodb', region_name="eu-north-1")
    except:
        #dev
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.getenv('AWS_REGION'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    table = dynamodb.Table('telemetry')
    response = table.scan()
    items = response.get('Items', [])
    data = response["Items"]

    # Parse timestamp column
    for item in data:
        raw_ts = item.get('ts')  # assuming the column is named 'timestamp'
        if raw_ts:
            item['ts'] = parser.parse(raw_ts)


    #print("items: ",items)
    df = pd.DataFrame(data)
    df = df.replace([np.nan, np.inf, -np.inf], "-")

    df = df[df.gps_lon!="-"][df.gps_lat!="-"]

    df = df.sort_values('ts')
    df['ts'] = df['ts'].apply(lambda x: x.isoformat())
    return df[['ts','gps_lat','gps_lon']]

df = getTelemetry()

@app.websocket("/ws/stream")
async def stream_data(websocket: WebSocket):
    await websocket.accept()
    try:
        for _, row in df.iterrows():
            await websocket.send_json(row.to_dict())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Client disconnected")

#this needs to be mounted and added after other routes are defined, otherwise those routes are not accessible
app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
@app.get("/")
async def serve_frontend(request: Request):
    print("Request headers: ",request.headers)
    print("IP address of the client making the request: ",request.host)
    return FileResponse(os.path.join(FRONTEND_BUILD_DIR, "index.html"))






