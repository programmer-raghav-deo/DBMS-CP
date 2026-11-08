import os
import shutil
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
#from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
# ==========================================
# 1. Server & Environment Setup
# ==========================================
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Agentic DB Optimizer API")

# Add this block to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite's default React port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in the .env file")

# Initialize LLM
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.1, api_key=groq_api_key)

# Global engine for the Agent 3 execution tool
db_engine = None

def get_database_connection(db_uri: str) -> SQLDatabase:
    """Creates a SQLAlchemy engine and returns a LangChain SQLDatabase."""
    global db_engine
    try:
        db_engine = create_engine(db_uri)
        # Test connection
        with db_engine.connect() as conn:
            pass
        return SQLDatabase(db_engine)
    except Exception as e:
        raise Exception(f"Database connection failed: {e}")

# ==========================================
# 2. Agent 3 Tool Definition
# ==========================================
@tool
def execute_sql_query(query: str) -> str:
    """
    Executes raw SQL queries (including CREATE INDEX or ALTER TABLE) on the database.
    Use this tool to apply the generated hash function/index to the database.
    """
    global db_engine
    if db_engine is None:
        return "Error: Database engine is not initialized."
    try:
        with db_engine.begin() as conn:
            conn.execute(text(query))
        return f"Successfully executed query: {query}"
    except Exception as e:
        return f"Database execution error: {str(e)}"

# ==========================================
# 3. Agent Logic
# ==========================================
def agent_1_analyze_db(db: SQLDatabase) -> str:
    """Reads schema and proposes columns for indexing."""
    schema_info = db.get_table_info()
    
    # Safely truncate massive schemas to avoid TPM rate limits
    max_chars = 15000 
    if len(schema_info) > max_chars:
        schema_info = schema_info[:max_chars] + "\n\n... [SCHEMA TRUNCATED TO FIT API LIMITS]"
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert database architect. Analyze the provided schema. Identify tables and large columns that would benefit from hash-based indexing. Provide a concise report of your findings."),
        ("user", "Database Schema:\n{schema}")
    ])
    chain = prompt | llm
    return chain.invoke({"schema": schema_info}).content

def agent_2_generate_hash_logic(agent_1_report: str) -> str:
    """Generates hash index logic based on Agent 1's report."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a performance optimization engineer. Based on the database analysis provided, generate the optimal SQL hash function or mathematical hashing logic (e.g., MD5, SHA256) to index the recommended column. Output ONLY the logic and a brief explanation."),
        ("user", "Database Analysis Report:\n{report}")
    ])
    chain = prompt | llm
    return chain.invoke({"report": agent_1_report}).content

def agent_3_apply_index(agent_1_report: str, hash_logic: str) -> str:
    """Writes the SQL and triggers the custom tool to execute it using LangGraph."""
    
    system_message = (
        "You are an expert Database Administrator. Using the target tables identified in the "
        "database analysis and the provided hash logic, write the exact SQL queries to create these indexes. "
        "You MUST use the `execute_sql_query` tool to run the queries you write."
    )
    
    tools = [execute_sql_query]
    
    # 1. Create the agent with NO modifier argument
    agent_executor = create_react_agent(llm, tools)
    
    user_prompt = f"Target Tables from Analysis:\n{agent_1_report}\n\nProposed Hash Logic:\n{hash_logic}"
    
    # 2. Pass the system instruction directly as the first message
    result = agent_executor.invoke({
        "messages": [
            ("system", system_message),
            ("user", user_prompt)
        ]
    })
    
    return result["messages"][-1].content

def run_pipeline(db_uri: str) -> Dict[str, Any]:
    """Orchestrates the 3 agents in sequence."""
    pipeline_results = {}
    try:
        db = get_database_connection(db_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    try:
        print("Running Agent 1...")
        pipeline_results["agent_1_report"] = agent_1_analyze_db(db)
        
        print("Running Agent 2...")
        pipeline_results["agent_2_hash_logic"] = agent_2_generate_hash_logic(pipeline_results["agent_1_report"])
        
        print("Running Agent 3...")
        pipeline_results["agent_3_execution_status"] = agent_3_apply_index(
            pipeline_results["agent_1_report"], 
            pipeline_results["agent_2_hash_logic"]
        )
    except Exception as e:
        pipeline_results["error"] = str(e)
        
    return pipeline_results

# ==========================================
# 4. FastAPI Endpoints
# ==========================================
@app.post("/api/optimize/mysql")
def optimize_mysql(mysql_uri: str = Form(..., description="e.g., mysql+pymysql://user:pass@localhost:3306/dbname")):
    """Endpoint for direct MySQL connection optimization."""
    results = run_pipeline(mysql_uri)
    return JSONResponse(content=results)

@app.post("/api/optimize/sqlite")
def optimize_sqlite(file: UploadFile = File(...)):
    """Endpoint to handle .db file uploads and optimize."""
    if not file.filename.endswith((".db", ".sqlite")):
        raise HTTPException(status_code=400, detail="Only .db or .sqlite files are allowed.")
    
    # Save uploaded file temporarily
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    sqlite_uri = f"sqlite:///{file_path}"
    
    # Run the agent pipeline
    results = run_pipeline(sqlite_uri)
    
    # Clean up the file after processing
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except PermissionError:
            pass # Handle OS-level locks if necessary
            
    return JSONResponse(content=results)

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)