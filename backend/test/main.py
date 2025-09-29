import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
from pydantic import BaseModel

load_dotenv()
DB_URL=os.getenv("DB_URL")


app = FastAPI()
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods={"*"},
    allow_headers={"*"}
)


engine = create_engine(DB_URL)


class QueryRequest(BaseModel):
    sql: str


@app.get("/")
def main():
    return { "message": "Hello world" }

@app.post("/query")
def run_query(req: QueryRequest):

    try:

        with engine.connect() as conn:
            df = pd.read_sql(text(req.sql), conn)
        
        return { "data": df.to_dict(orient="records") }
    
    except Exception as e: 

        return HTTPException(status_code=400, detail=str(e))
    

