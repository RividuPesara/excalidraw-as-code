import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import Scene  # noqa: E402

s = Scene()
top = s.title("Web App  ·  Architecture", "one api and one worker on one database")
s.legend(40, top + 20, ["built", "external", "planned"])

# column x positions and row y positions
COL = [40, 400, 760]
ROW = [top + 150, top + 340, top + 560]

s.box("browser", COL[0], ROW[0], 240, 70, "Browser\nReact app", "entry")
s.box("api", COL[1], ROW[0], 240, 70, "API\nREST and auth", "entry")
s.box("worker", COL[1], ROW[1], 240, 70, "Worker\nbackground jobs", "service")
s.box("db", COL[2], ROW[0], 240, 70, "Postgres\ndata and job queue", "store")
s.box("cache", COL[2], ROW[1], 240, 70, "Redis cache\nnext quarter", "store", "planned")
s.box("email", COL[1], ROW[2], 240, 60, "Email provider", "outside")

s.zone_around("backend", ["api", "worker"], "Backend", "same image in two processes")
s.zone_around("data", ["db", "cache"], "Data")
s.zone_around("ext", ["email"], "Outside")

s.connect("a_browser_api", "browser", "api", "HTTPS")
s.connect("a_api_db", "api", "db", "SQL")
s.connect("a_api_worker", "api", "worker", "enqueue", style="dashed")
s.connect("a_worker_cache", "worker", "cache", "warm", style="dotted")
s.connect("a_worker_email", "worker", "email", "send", style="dashed")

s.save(HERE / "out" / "web_app.excalidraw")
