import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from app import db, cve

app = FastAPI(title="CVE Watcher")

@app.on_event("startup")
def _init(): db.init()

@app.get("/", response_class=HTMLResponse)
def home():
    prods = db.list_products()
    li = "".join([f"<li>{p}</li>" for p in prods]) or "<li>(none)</li>"
    return f"<h1>CVE Watcher</h1><ul>{li}</ul>"

@app.get("/search")
def search(q: str = Query(..., description="keyword/product")):
    return {"query": q, "results": cve.search(q)}

@app.post("/watch")
def watch(q: str):
    db.add_product(q)
    return {"ok": True, "watching": q}
