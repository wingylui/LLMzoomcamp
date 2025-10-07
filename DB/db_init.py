import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RUN_TIMEZONE_CHECK = os.getenv('RUN_TIMEZONE_CHECK', '1') == '1'

TZ_INFO = os.getenv("TZ", "Australia/Perth")
tz = ZoneInfo(TZ_INFO)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),  
        port=int(os.getenv("POSTGRES_PORT", 5433)),
        database=os.getenv("POSTGRES_DB", "baking_assistant"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )


def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS feedback")
            cur.execute("DROP TABLE IF EXISTS conversations")

            cur.execute("""
                CREATE TABLE conversations (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    response_time FLOAT NOT NULL,
                    relevance TEXT NOT NULL,
                    relevance_explanation TEXT NOT NULL,
                    ans_prompt_tokens INTEGER NOT NULL,
                    ans_completion_tokens INTEGER NOT NULL,
                    ans_total_tokens INTEGER NOT NULL,
                    eval_prompt_tokens INTEGER NOT NULL,
                    eval_completion_tokens INTEGER NOT NULL,
                    eval_total_tokens INTEGER NOT NULL,
                    ans_cost FLOAT NOT NULL, 
                    eva_cost FLOAT NOT NULL,
                    total_cost FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE feedback (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT REFERENCES conversations(id),
                    feedback INTEGER NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
        conn.commit()
    finally:
        conn.close()



if __name__ == "__main__":
    print("Initializing database...")
    init_db()