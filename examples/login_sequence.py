import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import Scene  # noqa: E402

s = Scene()
top = s.title("Sign in", "browser, api and identity provider during an oauth login")

s.sequence("seq", 40, top + 50, ["Browser", "API", "Identity provider", "Postgres"], [
    ("Browser", "API", "GET /login"),
    ("API", "Browser", "302 to provider", "dashed"),
    ("Browser", "Identity provider", "sign in"),
    ("Identity provider", "API", "callback with code"),
    ("API", "Identity provider", "swap code for token"),
    ("API", "Postgres", "upsert user"),
    ("API", "API", "issue session"),
    ("API", "Browser", "set cookie", "dashed"),
])

s.save(HERE / "out" / "login_sequence.excalidraw")
