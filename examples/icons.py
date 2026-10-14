import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import Scene  # noqa: E402

AWS = "childishgirl/aws-architecture-icons.excalidrawlib"
K8S = "lowess/kubernetes-icons-set.excalidrawlib"

s = Scene()
top = s.title("Upload service", "icons come from the excalidraw community libraries")

s.icon("users", "anna-pastushko/architecture-diagram-components.excalidrawlib", "Users", 0, 0, 64, "Users")
s.icon("lb", "samu_x86/network-elements.excalidrawlib", "Load Balancer", 0, 0, 64, "Load balancer")
s.icon("pod", K8S, "pod", 0, 0, 64, "upload pods")
s.icon("s3", AWS, "S3", 0, 0, 64, "S3 bucket")
s.icon("redis", AWS, "MemoryDB for Redis", 0, 0, 64, "Redis")

s.connect("a1", "users", "lb", "HTTPS")
s.connect("a2", "lb", "pod")
s.connect("a3", "pod", "s3", "put")
s.connect("a4", "pod", "redis", "lock", style="dotted")

s.arrange([["users"], ["lb"], ["pod"], ["s3", "redis"]], 40, top + 70, gap=150, spread=90)
s.zone_around("cluster", ["pod"], "Cluster", pad=40)

s.save(HERE / "out" / "icons.excalidraw")
