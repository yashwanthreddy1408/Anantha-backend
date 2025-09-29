import os
from dotenv import load_dotenv
from openai import OpenAI
import json


load_dotenv()
GEMINI_API_KEY=os.getenv('GEMINI_API_KEY3')

def clean_response(res):
    if isinstance(res, str):
        s = res.strip()
        if s.startswith("```"):
            s = s.strip("`")
        if s.startswith("sql"):
            s = s.strip("sql")
        
        try:
            cleaned_response = json.loads(s)
        except json.JSONDecodeError:
            cleaned_response = s
    else:
        cleaned_response = res
    
    return cleaned_response

def sql_generator(query, type, retrieved_data=None):
    SYSTEM_PROMPT = f"""
You are an expert PostgreSQL query generator whose primary goal is to provide *accurate and efficient SQL* to answer user queries.

Database schema:
Table "public.argo_data_clean"
    Column         | Type                         | Collation | Nullable | Default
------------------+------------------------------+-----------+----------+---------
 profile          | integer                      |           |          | 
 date             | timestamp without time zone  |           |          | 
 latitude         | double precision             |           |          | 
 longitude        | double precision             |           |          | 
 pres_raw_dbar    | double precision             |           |          | 
 pres_adj_dbar    | double precision             |           |          | 
 temp_raw_c       | double precision             |           |          | 
 temp_adj_c       | double precision             |           |          | 
 psal_raw_psu     | double precision             |           |          | 
 psal_adj_psu     | double precision             |           |          | 
 float_id         | bigint                       |           |          | 
 unique_id        | bigint                       |           |          | 

User request:
{query}

Relevant float_ids from vector DB:
{retrieved_data}

Rules for generating SQL:
- Use only SELECT statements (no INSERT/UPDATE/DELETE/DDL).
- Table: argo_data_clean (do not quote or pluralize the name).
- Always wrap column names in double quotes, exactly as in schema.
- Always use relevant data type for that particular data you are representing
- Include "latitude" and "longitude" columns for any profiles being retrieved.
- For dates:
  • User input is TEXT in YYYY-MM-DD format.
  • Cast to DATE when filtering, e.g. "date"::DATE BETWEEN '2022-01-01' AND '2022-12-31'.
- "float_id" is BIGINT → wrap numeric IDs in single quotes only if treated as TEXT.
- Always terminate with a semicolon (;).
- Return output ONLY in valid JSON (see format below), no commentary or extra text.
- In general assume that data will be very large, so prefer performing aggregations most of the times.

Handling data volume:
1. For *small/narrow queries* (short date range, few float_ids, or single profile):
   - Return raw rows directly, including "latitude" and "longitude".
   - Set "data_size": "small", "aggregation_used": false, "suggest_plot": false.
2. For *large/broad queries* (long date ranges, many float_ids, or entire dataset):
   - Do NOT return all rows.
   - Use meaningful aggregates (AVG, MIN, MAX, COUNT, SUM) for numeric columns.
   - Group data to reduce volume (e.g., by month, float_id, or profile).
   - Include representative "latitude" and "longitude" values if relevant.
   - Set "data_size": "large", "aggregation_used": true, "suggest_plot": true.
3. If the volume is unclear, *default to aggregation and summarization*, and mark "data_size": "large".
4. Finally provide sources to cite for user to verify from the data you have. Dont invent sources yourself.

Optimization & Accuracy:
- Only select columns necessary to answer the user query.
- Ensure numeric data types are aggregated correctly and NULLs are handled appropriately.
- Always filter using relevant float_ids and date ranges to minimize output.
- Avoid sending excessive rows to the LLM; summarize whenever possible.

Return Format (JSON only):
{{
  "sql": "VALID_SQL_QUERY;",
  "data_size": "small" | "large",
  "aggregation_used": true | false,
  "suggest_plot": true | false,
  "sources_to_cite": "description of data sources used"
}}
"""


    try:
        client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": query
                }
            ],
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Ensure 'sql' key exists (your main.py checks for it)
        if 'sql_query' in parsed and 'sql' not in parsed:
            parsed['sql'] = parsed['sql_query']
        
        return parsed
    
    except Exception as e:
        print(f"Error in sql_generator: {e}")
        return {"error": str(e)}