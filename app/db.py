import sqlite3, os, pathlib
DB = pathlib.Path(os.getenv("DB_PATH", "cvewatch.db"))

def init():
    DB.parent.mkdir(parents=True, exist_ok=True)  # ensure directory exists
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS watch (
        id INTEGER PRIMARY KEY, product TEXT UNIQUE NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS seen (
        cve_id TEXT PRIMARY KEY, product TEXT, published TEXT)""")
    con.commit(); con.close()

def add_product(product:str):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO watch(product) VALUES (?)", (product,))
    con.commit(); con.close()

def list_products():
    con = sqlite3.connect(DB); cur = con.cursor()
    rows = cur.execute("SELECT product FROM watch ORDER BY product").fetchall()
    con.close(); return [r[0] for r in rows]

def mark_seen(cve_id, product, published):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO seen(cve_id,product,published) VALUES (?,?,?)",
                (cve_id, product, published))
    con.commit(); con.close()

def is_seen(cve_id)->bool:
    con = sqlite3.connect(DB); cur = con.cursor()
    row = cur.execute("SELECT 1 FROM seen WHERE cve_id=?", (cve_id,)).fetchone()
    con.close(); return row is not None

if __name__ == "__main__":
    init()
    print("DB ready at:", DB.resolve())

