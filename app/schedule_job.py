import os, time
from datetime import datetime
from app import db, cve, webex

def run_once():
    for product in db.list_products():
        results = cve.search(product, limit=5)
        new = []
        for r in results:
            if r["id"] and not db.is_seen(r["id"]):
                db.mark_seen(r["id"], product, r.get("published",""))
                new.append(r)
        if new:
            lines = "\n".join([f"- **{n['id']}** ({n['published']}): {n['summary'][:120]}…" for n in new])
            webex.notify(f"🚨 New CVEs for **{product}**:\n{lines}")

if __name__ == "__main__":
    db.init()
    minutes = int(os.getenv("POLL_MINUTES","15"))
    while True:
        run_once()
        time.sleep(60*minutes)
