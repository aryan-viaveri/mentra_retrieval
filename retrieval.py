import os
from collections import Counter
from typing import Dict, Any, List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client
from viaRAG.client import ViaRAGClient

# ---- Load environment and initialize clients ----
load_dotenv()

client = ViaRAGClient(os.environ["VIARAG_KEY"])
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ---- FastAPI app ----
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCORE_THRESHOLD = 0.35  # Adjust as needed


@app.get("/gif_metadata")
def fetch_gif_and_metadata(query: str = Query(...)):
    try:
        # Step 0: Rewrite the query to improve RAG alignment
        rewrite_prompt = f"""
        The user has entered the following search query:

        "{query}"

        Your task is to rewrite this query to better align with memory-based retrieval patterns, as used in systems like HyPE.

        The rewritten query should sound casual and slightly imprecise—something a user might type when trying to find a moment from memory. Think in terms of vibe, scene, or emotional anchor. Avoid technical or literal phrasing.

        Do not add explanations. Output only the rewritten query as a single line.
        """
        query = client.direct_query(rewrite_prompt)["response"].strip()

        # Step 1: Get top-k context chunks
        chunks: List[Dict[str, Any]] = client.match_context(query, top_k=5)

        # Step 2: Count gif_path occurrences
        gif_paths = [
            chunk["metadata"].get("gif_path")
            for chunk in chunks
            if "metadata" in chunk and "gif_path" in chunk["metadata"]
        ]
        if not gif_paths:
            raise ValueError("No gif_path metadata found in chunks.")

        most_common_path, _ = Counter(gif_paths).most_common(1)[0]

        # Step 3: Filter chunks to those with the most_common_path
        matching_chunks = [
            chunk for chunk in chunks
            if chunk["metadata"].get("gif_path") == most_common_path
        ]
        if not matching_chunks:
            raise ValueError("No chunks match the most common gif_path.")

        max_score = max(chunk.get("score", 0.0) for chunk in matching_chunks)
        if max_score < SCORE_THRESHOLD:
            raise ValueError("Top matching chunk score below threshold.")

        # Step 4: Query Supabase for metadata
        response = supabase.table("gif_metadata").select("*").eq("file_path", most_common_path).limit(1).execute()
        if not response.data:
            raise ValueError(f"No metadata found in Supabase for gif path: {most_common_path}")

        # Step 5: Generate rewritten summary
        response.data[0]["summary"] = client.direct_query(
            "Rewrite the following as a vivid and elegant memory,in 3 to 8 lines."
            "It should feel warm and grounded, something the user can fondly reflect on without being sentimental or nostalgic."
            "The tone should be almost factual, but with poetic clarity and grace. "
            "Add light context where it fits. "
            "Avoid anything overly dramatic, cheesy, or emotionally indulgent. "
            f"Rewrite this: {response.data[0]['summary']}"
        )["response"]

        return JSONResponse(content=response.data[0])

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Run directly ----
if __name__ == "__main__":
    uvicorn.run("retrieval:app", host="0.0.0.0", port=8000, reload=True)
