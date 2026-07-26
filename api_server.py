from fastapi import FastAPI, HTTPException
import sqlite3
import json
import os

app = FastAPI(title="JARVIS-V6 Quant API", version="1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data_lake", "quant.db")

def get_db():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="Database not ready. Backend is still syncing.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def root():
    return {"status": "online", "message": "JARVIS-V6 API Server"}

@app.get("/api/v1/predictions")
def get_all_predictions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM predictions").fetchall()
    conn.close()
    
    results = []
    for row in rows:
        data = dict(row)
        if data.get('JSON_Blob'):
            data['JSON_Blob'] = json.loads(data['JSON_Blob'])
        results.append(data)
    return results

@app.get("/api/v1/asset/{ticker}")
def get_asset(ticker: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM predictions WHERE Ticker = ?", (ticker,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    data = dict(row)
    if data.get('JSON_Blob'):
        data['JSON_Blob'] = json.loads(data['JSON_Blob'])
    return data

@app.get("/api/v1/leaderboard")
def get_leaderboard():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM leaderboard").fetchall()
        return [dict(row) for row in rows]
    except:
        return []
    finally:
        conn.close()
