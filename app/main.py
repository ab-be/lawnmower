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

import joblib
import os

import random

'''
#ROS2
from fastapi import FastAPI
import rclpy
from std_msgs.msg import Float32

app = FastAPI()
rclpy.init()

battery_state = {"value": None}

def battery_callback(msg):
    battery_state["value"] = msg.data

node = rclpy.create_node('backend_listener')
subscription = node.create_subscription(Float32, '/battery_state', battery_callback, 10)

@app.get("/battery")
def get_battery():
    return {"battery": battery_state["value"]}

'''


load_dotenv()


#----------------------------------------
# Middleware
#----------------------------------------
app = FastAPI()

#origins = ['http://localhost','http://localhost:3000','http://127.0.0.1:5173', 'http://16.171.39.45', 'http://16.171.39.45:8000', 'http://16.171.39.45:3000', 'http://16.171.39.45:5173','https://test.lawnmower.publicvm.com','https://lawnmower.publicvm.com']
origins = ['http://localhost','http://localhost:3000','http://127.0.0.1:5173', 'http://16.171.39.45', 'http://16.171.39.45:8000', 'http://16.171.39.45:3000', 'http://16.171.39.45:5173','https://test.lawnmower.publicvm.com','https://lawnmower.publicvm.com']
#origins = ["*"]
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

@app.get("/health2")
async def health_check():
    return {"status":"healthy"}

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
        raw_ts = item.get('ts')  
        if raw_ts:
            item['ts'] = parser.parse(raw_ts)


    #print("items: ",items)
    df = pd.DataFrame(data)
    df = df.replace([np.nan, np.inf, -np.inf], "-")

    df = df[df.gps_lon!="-"][df.gps_lat!="-"]

    df = df.sort_values('ts')
    df['ts'] = df['ts'].apply(lambda x: x.isoformat())


    #scale & predict
    ''' BATTERY % https://gitlab.labranet.jamk.fi/AH2789/mmit-2025-lawn-mower/-/blob/main/machine-learning/api/services/battery_service.py
    [
                'battery_pct', 'battery_v',
                'blade_current_a', 'wheel_current_l_a', 'wheel_current_r_a',
                'speed_mps', 'gps_accuracy_m', 'satellite_count',
                'imu_tilt_deg', 'motor_temp_c', 'chassis_temp_c',
                'blade_vibration_rms', 'filter_dp_pa',
                'conn_signal_dbm', 'conn_quality',
                'uplink_latency_ms', 'downlink_latency_ms', 'packet_loss_pct'
            ]

    '''
    #BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    #SCALER_MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "battery_predictor_scaler.pkl")
    #PRED_MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "battery_predictor_model.pkl")
    #battery_scaler = joblib.load(SCALER_MODEL_PATH)
    #battery_predictor = joblib.load(PRED_MODEL_PATH) 
    #battery_features = [
    #            'battery_pct', 'battery_v',
    #            'blade_current_a', 'wheel_current_l_a', 'wheel_current_r_a',
    #            'speed_mps', 'gps_accuracy_m', 'satellite_count',
    #            'imu_tilt_deg', 'motor_temp_c', 'chassis_temp_c',
    #            'blade_vibration_rms', 'filter_dp_pa',
    #            'conn_signal_dbm', 'conn_quality',
    #            'uplink_latency_ms', 'downlink_latency_ms', 'packet_loss_pct'
    #        ]
    #features_scaled = battery_scaler.transform(df[battery_features])
    #predicted_drop = float(battery_predictor.predict(features_scaled)[0])
    #print("predicted_drop: ",predicted_drop)

    #test
    df["predicted_failure_%"] = np.random.randint(0, 101, size=len(df))
    df["predicted_battery_replacement_%"] = np.random.randint(0, 101, size=len(df))
    df["predicted_obstacle_vicinity_%"] = np.random.randint(0, 101, size=len(df))

    return df[['ts','gps_lat','gps_lon','predicted_failure_%','predicted_battery_replacement_%','predicted_obstacle_vicinity_%']]

df = getTelemetry()

@app.websocket("/ws")
async def stream_data(websocket: WebSocket):
    await websocket.accept()
    try:
        for _, row in df.iterrows():
            await websocket.send_json(row.to_dict())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")


#PROD
#this needs to be mounted and added after other routes are defined, otherwise those routes are not accessible

app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
@app.get("/")
async def serve_frontend(request: Request):
    print("Request headers: ",request.headers)
    print("IP address of the client making the request: ",request.host)
    return FileResponse(os.path.join(FRONTEND_BUILD_DIR, "index.html"))
