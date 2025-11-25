import os, requests

BASE = os.getenv("CVE_API_BASE","https://services.nvd.nist.gov/rest/json/cves/2.0")

def search(keyword:str, limit=10):
    # NVD v2.0 basic keyword search; unauth = rate-limited (OK for demo)
    r = requests.get(BASE, params={"keywordSearch": keyword, "resultsPerPage": limit}, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        out.append({
            "id": cve.get("id"),
            "published": cve.get("published"),
            "summary": (cve.get("descriptions") or [{}])[0].get("value","")
        })
    return out
