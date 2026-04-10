from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json

app = FastAPI()

# CORS (required for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
df = pd.read_csv("replay_results.csv")

# ✅ SAFE parsing (only if column exists)
if "psp_ranking" in df.columns:
    df["psp_ranking"] = df["psp_ranking"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else x
    )

@app.get("/")
def root():
    return {"status": "API running"}

@app.get("/metrics")
def get_metrics():
    total_txns = len(df)
    avg_regret = df["regret"].mean() if "regret" in df.columns else 0
    osr = (df["regret"] == 0).mean() if "regret" in df.columns else 0

    return {
        "total_txns": int(total_txns),
        "avg_regret": float(avg_regret),
        "osr": float(osr),
    }

@app.get("/transactions")
def get_transactions():
    cols = ["txn_id", "chosen_psp", "best_psp", "regret"]
    existing_cols = [c for c in cols if c in df.columns]
    return df[existing_cols].to_dict(orient="records")

@app.get("/transaction/{txn_id}")
def get_transaction(txn_id: str):
    if "txn_id" not in df.columns:
        return {"error": "txn_id column missing"}

    txn = df[df["txn_id"] == txn_id]

    if txn.empty:
        return {"error": "Transaction not found"}

    txn = txn.iloc[0]

    return {
        "txn_id": txn.get("txn_id"),
        "chosen_psp": txn.get("chosen_psp"),
        "best_psp": txn.get("best_psp"),
        "regret": txn.get("regret"),
        "psp_ranking": txn.get("psp_ranking", []),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)