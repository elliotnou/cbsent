import os
import json
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are the FinSENT Policy Analyst, an expert on monetary policy sentiment for the Federal Reserve (Fed) and Bank of Canada (BoC).

You have access to a database of central bank transcripts analyzed sentence-by-sentence using a fine-tuned DistilBERT model. Each sentence has:
- stance_score: -1.0 (dovish/accommodative) to +1.0 (hawkish/restrictive)
- impact_weight: 0.0 to 1.0 based on topic relevance (Inflation=1.0, Guidance=1.0, Employment=0.7, Growth=0.7, Boilerplate=0.0)
- topic: one of Inflation, Growth, Employment, Guidance, or Boilerplate
- reasoning: explanation of the classification

Divergence = Fed sentiment - BoC sentiment. Positive divergence means the Fed is more hawkish than the BoC.
Bank names in the database are exactly "Fed" and "BoC".

Always use your tools to look up data before answering — do not guess or make up numbers. Be precise with scores (3 decimal places). When comparing banks, query both. Keep answers concise but data-driven."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sentiment_summary",
            "description": "Get average stance scores grouped by date for a specific bank. Use this to see how a bank's sentiment has evolved over time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bank": {"type": "string", "description": "Bank name: 'Fed' or 'BoC'"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (optional)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (optional)"}
                },
                "required": ["bank"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transcripts",
            "description": "List transcripts with their aggregate sentiment score. Use to find specific releases or see what transcripts exist in a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bank": {"type": "string", "description": "Filter by bank: 'Fed' or 'BoC' (optional)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (optional)"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD (optional)"},
                    "limit": {"type": "integer", "description": "Max results to return (default 10)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transcript_sentences",
            "description": "Get the full sentence-level breakdown for a specific transcript. Use this to drill into WHY a transcript scored the way it did.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transcript_id": {"type": "integer", "description": "The transcript ID to retrieve sentences for"}
                },
                "required": ["transcript_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_sentences",
            "description": "Search sentence text for a keyword, with optional bank and topic filters. Use to find what central banks said about specific subjects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Text to search for (case-insensitive partial match)"},
                    "bank": {"type": "string", "description": "Filter by bank: 'Fed' or 'BoC' (optional)"},
                    "topic": {"type": "string", "description": "Filter by topic: Inflation, Growth, Employment, Guidance, Boilerplate (optional)"}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_divergence",
            "description": "Get the Fed-vs-BoC sentiment divergence over time. Returns each date's Fed score, BoC score, and divergence (Fed - BoC).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (optional)"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD (optional)"}
                },
                "required": []
            }
        }
    }
]


def _get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is missing")
    return psycopg2.connect(db_url)


def _query(sql, params=None):
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def run_get_sentiment_summary(args):
    bank = args["bank"]
    conditions = ["t.bank_name = %s"]
    params = [bank]
    if args.get("start_date"):
        conditions.append("t.publish_date >= %s")
        params.append(args["start_date"])
    if args.get("end_date"):
        conditions.append("t.publish_date <= %s")
        params.append(args["end_date"])
    where = " AND ".join(conditions)
    sql = f"""
        SELECT t.publish_date::text as date, AVG(ts.stance_score) as avg_sentiment,
               COUNT(*) as sentence_count
        FROM transcript_sentences ts
        JOIN transcripts t ON ts.transcript_id = t.id
        WHERE {where}
        GROUP BY t.publish_date
        ORDER BY t.publish_date
    """
    return _query(sql, params)


def run_get_transcripts(args):
    conditions = []
    params = []
    if args.get("bank"):
        conditions.append("t.bank_name = %s")
        params.append(args["bank"])
    if args.get("start_date"):
        conditions.append("t.publish_date >= %s")
        params.append(args["start_date"])
    if args.get("end_date"):
        conditions.append("t.publish_date <= %s")
        params.append(args["end_date"])
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    limit = args.get("limit", 10)
    sql = f"""
        SELECT t.id, t.bank_name as bank, t.publish_date::text as date,
               AVG(ts.stance_score) as sentiment, COUNT(ts.id) as sentence_count
        FROM transcripts t
        LEFT JOIN transcript_sentences ts ON t.id = ts.transcript_id
        {where}
        GROUP BY t.id, t.bank_name, t.publish_date
        ORDER BY t.publish_date DESC
        LIMIT %s
    """
    params.append(limit)
    return _query(sql, params)


def run_get_transcript_sentences(args):
    sql = """
        SELECT ts.sentence_text as text, ts.stance_score as score,
               ts.impact_weight as impact, ts.topic, ts.reasoning
        FROM transcript_sentences ts
        WHERE ts.transcript_id = %s
        ORDER BY ts.id ASC
        LIMIT 50
    """
    return _query(sql, (args["transcript_id"],))


def run_search_sentences(args):
    conditions = ["ts.sentence_text ILIKE %s"]
    params = [f"%{args['keyword']}%"]
    if args.get("bank"):
        conditions.append("t.bank_name = %s")
        params.append(args["bank"])
    if args.get("topic"):
        conditions.append("ts.topic = %s")
        params.append(args["topic"])
    where = " AND ".join(conditions)
    sql = f"""
        SELECT ts.sentence_text as text, ts.stance_score as score,
               ts.topic, t.bank_name as bank, t.publish_date::text as date
        FROM transcript_sentences ts
        JOIN transcripts t ON ts.transcript_id = t.id
        WHERE {where}
        ORDER BY t.publish_date DESC
        LIMIT 20
    """
    return _query(sql, params)


def run_get_divergence(args):
    conditions = []
    params = []
    if args.get("start_date"):
        conditions.append("t.publish_date >= %s")
        params.append(args["start_date"])
    if args.get("end_date"):
        conditions.append("t.publish_date <= %s")
        params.append(args["end_date"])
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT t.publish_date::text as date, t.bank_name as bank,
               AVG(ts.stance_score) as sentiment
        FROM transcript_sentences ts
        JOIN transcripts t ON ts.transcript_id = t.id
        {where}
        GROUP BY t.publish_date, t.bank_name
        ORDER BY t.publish_date
    """
    rows = _query(sql, params)
    # Pivot into divergence format
    by_date = {}
    for row in rows:
        d = row["date"]
        if d not in by_date:
            by_date[d] = {"date": d}
        if row["bank"] == "Fed":
            by_date[d]["fed"] = round(float(row["sentiment"]), 3)
        elif row["bank"] == "BoC":
            by_date[d]["boc"] = round(float(row["sentiment"]), 3)
    result = []
    for d in sorted(by_date.keys()):
        entry = by_date[d]
        fed = entry.get("fed", 0)
        boc = entry.get("boc", 0)
        entry["divergence"] = round(fed - boc, 3)
        result.append(entry)
    return result


TOOL_MAP = {
    "get_sentiment_summary": run_get_sentiment_summary,
    "get_transcripts": run_get_transcripts,
    "get_transcript_sentences": run_get_transcript_sentences,
    "search_sentences": run_search_sentences,
    "get_divergence": run_get_divergence,
}


def execute_tool(name, arguments):
    fn = TOOL_MAP.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(arguments)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


MAX_ITERATIONS = 5


def run_agent(user_message: str, history: list) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    tool_calls_made = []

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        assistant_msg = choice.message

        # Append assistant message to conversation
        msg_dict = {"role": "assistant", "content": assistant_msg.content or ""}
        if assistant_msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in assistant_msg.tool_calls
            ]
        messages.append(msg_dict)

        if not assistant_msg.tool_calls:
            return {
                "response": assistant_msg.content or "",
                "tool_calls_made": tool_calls_made
            }

        for tc in assistant_msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            tool_calls_made.append({"tool": fn_name, "args": fn_args})

            result = execute_tool(fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result
            })

    # Hit max iterations — get a final answer without tools
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return {
        "response": response.choices[0].message.content or "",
        "tool_calls_made": tool_calls_made
    }
