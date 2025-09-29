import os 
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json
import asyncio
from query_enhancement.enhance import query_enhancer
from query_enhancement.classify import query_classifier
from query_enhancement.filters import generate_filters
from store_in_vector_db.vector_db import query_documents
from generate_sql.sql import sql_generator
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from retrieve_data_from_db.postgres_db import retrieve_data_from_postgres
from final_ans.final_llm_call import get_ans_with_relevant_data

from typing import Optional


load_dotenv()

app = FastAPI()
origins = ["http://localhost:5173","http://localhost:8080", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # <- must be a list
    allow_headers=["*"]    # <- must be a list
)
history = [{"question": "hi", "answer": "Hello, I am float chat, here to assist you with oceanographic data, feel free to ask any question related to it."}]


class TableResponse(BaseModel):
    type: str
    message: str
    raw_data: list[dict]
    columns: list[str]
    csv_url: str

class PlotResponse(BaseModel):
    type: str
    message: str
    csv_url: str

class TextResponse(BaseModel):
    type: str
    message: str

class QueryRequest(BaseModel):
    tab: str
    query: str
    language: str
    imageData: Optional[str] = None

def clean_response(res):
    """
    Ensure that the response is always a dict.
    If it's a string, try to parse as JSON.
    If parsing fails, wrap it in {'reply': str(res)}.
    """
    if isinstance(res, dict):
        return res
    if isinstance(res, str):
        try:
            return json.loads(res)
        except json.JSONDecodeError:
            return {"reply": res}
    return {"reply": str(res)}


async def save_pg_data_async(pg_data, path):
    await asyncio.to_thread(pg_data.to_csv, path, index=False)


def text_answer(query, language):
    res = clean_response(query_enhancer(query, language, []))
    print("Query:", query)
    
    # reply
    if res.get('reply') is not None:
        return {"text": res['reply']}

    if res.get('enhanced_query') is not None:
        enhanced_query = res['enhanced_query']
        print("Enhanced query:", enhanced_query)

        res = clean_response(query_classifier(enhanced_query))

        if res.get('search_type') is not None:
            search_type = res['search_type']
            print("Search type:", search_type)

            # direct SQL
            if search_type == "sql":
                res = clean_response(sql_generator(enhanced_query, 'theory'))
                
                if res.get('error'):
                    return {"text": f"Error generating SQL: {res['error']}"}
                
                if res.get('sql') is not None:
                    sql = res['sql']
                    print("SQL:", sql, end="\n\n")

                    pg_data = retrieve_data_from_postgres(sql)
                    
                    if pg_data.empty:
                        return {"text": "No data found for your query. Please try a different query."}
                    
                    pg_data_json = pg_data.to_json(orient="records")

                    sources_to_cite = None
                    if res.get('sources_to_cite'):
                        sources_to_cite = res['sources_to_cite']
                        print("Sources to cite:", sources_to_cite, end="\n\n")

                    final_ans_text = get_ans_with_relevant_data(enhanced_query, pg_data_json, [], sources_to_cite, language)
                    print("Final ans:", final_ans_text)

                    return {"text": final_ans_text}
                else:
                    return {"text": "Could not generate SQL query. Please rephrase your question."}
                
            elif search_type == "vector":
                res = clean_response(generate_filters(enhanced_query))
                print("Retrieved vector data:", res)

                if res.get('where') is not None:
                    where_filters = res['where']
                    res = query_documents(enhanced_query, where_filters)
                    vector_ids = res['ids'][0]

                    print("Vector IDs:", vector_ids)

                    res = clean_response(sql_generator(enhanced_query, 'theory', vector_ids))
                    print("SQL response:", res)
                    
                    if res.get('error'):
                        return {"text": f"Error generating SQL: {res['error']}"}
                    
                    if res.get('sql') is not None:
                        sql = res['sql']
                        print("SQL:", sql)

                        pg_data = retrieve_data_from_postgres(sql)
                        
                        if pg_data.empty:
                            return {"text": "No data found for your query. Please try a different query."}
                        
                        pg_data_json = pg_data.to_json(orient="records")

                        sources_to_cite = None
                        if res.get('sources_to_cite'):
                            sources_to_cite = res['sources_to_cite']
                            print("Sources to cite:", sources_to_cite, end="\n\n")

                        final_ans_text = get_ans_with_relevant_data(enhanced_query, pg_data_json, [], sources_to_cite, language)
                        print("Final ans:", final_ans_text)

                        return {"text": final_ans_text}
                    else:
                        return {"text": "Could not generate SQL query. Please rephrase your question."}
    
    return {"text": "I couldn't process your query. Please try again."}


def table_answer(query, language="english"):
    res = clean_response(query_enhancer(query, language, []))
    
    # reply
    if res.get('reply') is not None:
        return {"text": res['reply'], "csv_url": None}

    if res.get('enhanced_query') is not None:
        enhanced_query = res['enhanced_query']
        print("Enhanced query:", enhanced_query)

        res = clean_response(query_classifier(enhanced_query))

        if res.get('search_type') is not None:
            search_type = res['search_type']
            print("Search type:", search_type)

            # direct SQL
            if search_type == "sql":
                res = clean_response(sql_generator(enhanced_query, 'table'))
                
                if res.get('error'):
                    return {"text": f"Error generating SQL: {res['error']}", "csv_url": None}
                
                if res.get('sql') is not None:
                    sql = res['sql']
                    print("SQL:", sql)

                    pg_data = retrieve_data_from_postgres(sql)
                    
                    if pg_data.empty:
                        return {"text": "No data found for your query.", "csv_url": None}
                    
                    if res.get('sources_to_cite'):
                        sources_to_cite = res['sources_to_cite']
                        print("Sources to cite:", sources_to_cite, end="\n\n")

                    # Create static/tables directory if it doesn't exist
                    os.makedirs('static/tables', exist_ok=True)
                    
                    csv_path = 'static/tables/userId_chatId_uniqueId.csv'
                    asyncio.run(save_pg_data_async(pg_data, csv_path))

                    return {
                        "text": f"Query returned {len(pg_data)} row(s). Showing first {min(len(pg_data), 10)} rows.",
                        "csv_url": csv_path
                    }
                else:
                    return {"text": "Could not generate SQL query.", "csv_url": None}
                
            elif search_type == "vector":
                res = clean_response(generate_filters(enhanced_query))
                print("Retrieved vector data:", res)

                if res.get('where') is not None:
                    where_filters = res['where']
                    res = query_documents(enhanced_query, where_filters)
                    vector_ids = res['ids'][0]

                    print("Vector IDs:", vector_ids)

                    res = clean_response(sql_generator(enhanced_query, 'table', vector_ids))
                    print("SQL response:", res)
                    
                    if res.get('error'):
                        return {"text": f"Error generating SQL: {res['error']}", "csv_url": None}
                    
                    if res.get('sql') is not None:
                        sql = res['sql']
                        print("SQL:", sql)

                        pg_data = retrieve_data_from_postgres(sql)
                        
                        if pg_data.empty:
                            return {"text": "No data found for your query.", "csv_url": None}
                        
                        if res.get('sources_to_cite'):
                            sources_to_cite = res['sources_to_cite']
                            print("Sources to cite:", sources_to_cite, end="\n\n")

                        # Create static/tables directory if it doesn't exist
                        os.makedirs('static/tables', exist_ok=True)
                        
                        csv_path = 'static/tables/userId_chatId_uniqueId.csv'
                        asyncio.run(save_pg_data_async(pg_data, csv_path))

                        return {
                            "text": f"Query returned {len(pg_data)} row(s). Showing first {min(len(pg_data), 10)} rows.",
                            "csv_url": csv_path
                        }
                    else:
                        return {"text": "Could not generate SQL query.", "csv_url": None}
    
    return {"text": "I couldn't process your query.", "csv_url": None}


def plot_answer(query, language="english"):
    res = clean_response(query_enhancer(query, language, []))
    
    # reply
    if res.get('reply') is not None:
        return {"text": res['reply'], "csv_url": None}

    if res.get('enhanced_query') is not None:
        enhanced_query = res['enhanced_query']
        print("Enhanced query:", enhanced_query)

        res = clean_response(query_classifier(enhanced_query))

        if res.get('search_type') is not None:
            search_type = res['search_type']
            print("Search type:", search_type)

            # direct SQL
            if search_type == "sql":
                res = clean_response(sql_generator(enhanced_query, 'plot'))
                
                if res.get('error'):
                    return {"text": f"Error generating SQL: {res['error']}", "csv_url": None}
                
                if res.get('sql') is not None:
                    sql = res['sql']
                    print("SQL:", sql)

                    pg_data = retrieve_data_from_postgres(sql)
                    
                    if pg_data.empty:
                        return {"text": "No data found for your query.", "csv_url": None}
                    
                    if res.get('sources_to_cite'):
                        sources_to_cite = res['sources_to_cite']
                        print("Sources to cite:", sources_to_cite, end="\n\n")

                    # Create static/plots directory if it doesn't exist
                    os.makedirs('static/plots', exist_ok=True)
                    
                    csv_path = 'static/plots/userId_chatId_uniqueId.csv'
                    asyncio.run(save_pg_data_async(pg_data, csv_path))

                    return {
                        "text": f"Query returned {len(pg_data)} row(s). Data prepared for plotting visualization.",
                        "csv_url": csv_path
                    }
                else:
                    return {"text": "Could not generate SQL query.", "csv_url": None}
                
            elif search_type == "vector":
                res = clean_response(generate_filters(enhanced_query))
                print("Retrieved vector data:", res)

                if res.get('where') is not None:
                    where_filters = res['where']
                    res = query_documents(enhanced_query, where_filters)
                    vector_ids = res['ids'][0]

                    print("Vector IDs:", vector_ids)

                    res = clean_response(sql_generator(enhanced_query, 'plot', vector_ids))
                    print("SQL response:", res)
                    
                    if res.get('error'):
                        return {"text": f"Error generating SQL: {res['error']}", "csv_url": None}
                    
                    if res.get('sql') is not None:
                        sql = res['sql']
                        print("SQL:", sql)

                        pg_data = retrieve_data_from_postgres(sql)
                        
                        if pg_data.empty:
                            return {"text": "No data found for your query.", "csv_url": None}
                        
                        if res.get('sources_to_cite'):
                            sources_to_cite = res['sources_to_cite']
                            print("Sources to cite:", sources_to_cite, end="\n\n")

                        # Create static/plots directory if it doesn't exist
                        os.makedirs('static/plots', exist_ok=True)
                        
                        csv_path = 'static/plots/userId_chatId_uniqueId.csv'
                        asyncio.run(save_pg_data_async(pg_data, csv_path))

                        return {
                            "text": f"Query returned {len(pg_data)} row(s). Data prepared for plotting visualization.",
                            "csv_url": csv_path
                        }
                    else:
                        return {"text": "Could not generate SQL query.", "csv_url": None}
    
    return {"text": "I couldn't process your query.", "csv_url": None}
    
@app.get("/")
def main():
    return {"message": "Welcome to Float chat, what do you want to know today... ?"}

static_path = Path(__file__).parent / "static"
print(f"Static path: {static_path}")

app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.post("/query")
def safe_api_call(func, *args, retries=3, delay=2, **kwargs):
    """
    Wrapper to safely call external APIs with retry logic.
    Raises HTTPException with 503 if API fails after retries.
    """
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    raise HTTPException(
        status_code=503,
        detail="External API temporarily unavailable. Please try again later."
    )
    
def get_answer(req: QueryRequest):
    global history

    try:
        tab_chosen = req.tab.lower() if req.tab and req.tab.lower() in ["table", "plot", "theory"] else "theory"

        # Validate query
        if not req.query or req.query.strip() == "":
            raise HTTPException(status_code=400, detail="Query can't be empty")

        user_query = req.query.strip()

        # Handle "table" tab
        if tab_chosen == "table":
            answer = safe_api_call(table_answer, user_query, req.language)

            if not answer or 'text' not in answer:
                raise HTTPException(status_code=500, detail="Invalid response from table_answer")

            text = answer['text']
            url = answer.get('csv_url')

            if not url or not os.path.exists(url):
                return TextResponse(type=tab_chosen, message=text)

            try:
                df = pd.read_csv(url)
            except Exception as e:
                print(f"Error reading CSV: {e}")
                return TextResponse(type=tab_chosen, message=text)

            return TableResponse(
                type=tab_chosen,
                message=text,
                raw_data=df.head(10).to_dict(orient="records"),
                columns=df.columns.to_list(),
                csv_url=url
            )

        # Handle "plot" tab
        elif tab_chosen == "plot":
            answer = safe_api_call(plot_answer, user_query, req.language)

            if not answer or 'text' not in answer:
                raise HTTPException(status_code=500, detail="Invalid response from plot_answer")

            text = answer['text']
            url = answer.get('csv_url')

            if not url or not os.path.exists(url):
                return TextResponse(type=tab_chosen, message=text)

            return PlotResponse(
                type=tab_chosen,
                message=text,
                csv_url=url
            )

        # Handle "theory" or default tab
        else:
            answer = safe_api_call(text_answer, user_query, req.language)

            if not answer or 'text' not in answer:
                raise HTTPException(status_code=500, detail="Invalid response from text_answer")

            text = answer['text']

            return TextResponse(
                type=tab_chosen,
                message=text
            )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        print(f"Exception in get_answer: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
