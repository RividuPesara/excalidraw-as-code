import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import SIZE, Scene  # noqa: E402

s = Scene()
s.text("title", 40, 0, "Web App  ·  Architecture", SIZE["head"], "head")
s.text("subtitle", 40, 46, "one api and one worker on one database", SIZE["note"], "soft")
s.legend(40, 80, ["built", "external", "planned"])

# column x positions and row y positions
COL = [40, 400, 800]
ROW = [220, 410]

s.box("browser", COL[0], ROW[0], 240, 70, "Browser\nReact app", "entry")

s.zone("backend", 360, 130, 320, 420, "Backend", "same image in two processes")
s.box("api", COL[1], ROW[0], 240, 70, "API\nREST and auth", "entry")
s.box("worker", COL[1], ROW[1], 240, 70, "Worker\nbackground jobs", "service")

s.zone("data", 760, 130, 320, 420, "Data")
s.box("db", COL[2], ROW[0], 240, 70, "Postgres\ndata and job queue", "store")
s.box("cache", COL[2], ROW[1], 240, 70, "Redis cache\nnext quarter", "store", "planned")

s.zone("ext", 360, 630, 320, 190, "Outside")
s.box("email", COL[1], 720, 240, 60, "Email provider", "outside")

s.connect("a_browser_api", "browser", "api", "HTTPS")
s.connect("a_api_db", "api", "db", "SQL")
s.connect("a_api_worker", "api", "worker", "enqueue", style="dashed")
s.connect("a_worker_cache", "worker", "cache", "warm", style="dotted")
s.connect("a_worker_email", "worker", "email", "send", style="dashed")

s.save(HERE / "out" / "web_app.excalidraw")
