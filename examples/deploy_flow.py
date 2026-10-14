import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import Scene  # noqa: E402

# sketch style switches to the hand drawn font and rough strokes
s = Scene(style="sketch")
top = s.title("Release", "what happens after a merge to main")

s.box("merge", 0, 0, label="Merge to main", kind="entry", shape="ellipse")
s.box("ci", 0, 0, label="Build and test", kind="service")
s.box("green", 0, 0, label="Tests pass?", kind="gate", shape="diamond")
s.box("stage", 0, 0, label="Deploy to staging", kind="service")
s.box("fix", 0, 0, label="Fix and push", kind="alert")
s.box("ok", 0, 0, label="Smoke ok?", kind="gate", shape="diamond")
s.box("prod", 0, 0, label="Deploy to prod", kind="focus")
s.box("rollback", 0, 0, label="Roll back", kind="alert", state="planned")

s.connect("a1", "merge", "ci")
s.connect("a2", "ci", "green")
s.connect("a3", "green", "stage", "yes")
s.connect("a4", "green", "fix", "no")
s.connect("a5", "stage", "ok")
s.connect("a6", "ok", "prod", "yes")
s.connect("a7", "ok", "rollback", "no", style="dashed")

s.arrange([["merge"], ["ci"], ["green"], ["stage", "fix"], ["ok"], ["prod", "rollback"]], 40, top + 60,
          direction="down", gap=70, spread=80)
s.connect("a8", "fix", "ci", "retry", style="dashed")
s.note("tip", 640, top + 60, "Staging and prod share\none image tag so a pass\non staging is the real build")

s.save(HERE / "out" / "deploy_flow.excalidraw")
