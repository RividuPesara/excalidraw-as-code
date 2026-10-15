import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import uml  # noqa: E402
from excalidraw import Scene  # noqa: E402


def components(version: int) -> Scene:
    s = Scene()
    uml.frame(s, "frame", 0, 0, 1060, 560, "cmp", "Orders")
    uml.subsystem(s, "core", 360, 80, 400, 420, "Order service")
    uml.component(s, "api", 400, 150, 320, 70, "Order API")
    uml.component(s, "rules", 400, 280, 150, 70, "Pricing")
    uml.component(s, "repo", 570, 280, 150, 70, "Repository")
    uml.store(s, "db", 880, 390, 140, 110, "orders\ndatabase")
    uml.component(s, "client", 60, 150, 180, 70, "Web shop", "component")
    uml.assembly(s, "i_orders", "client", "api", "orders")
    s.connect("w_rules", "api", "rules", style="dashed")
    s.connect("w_repo", "api", "repo", style="dashed")
    s.connect("w_sql", "repo", "db", "SQL", label_size=15)
    if version >= 1:
        # what a version adds gets the highlight outline
        uml.component(s, "cache", 400, 400, 320, 70, "Price cache")
        s.connect("w_cache", "rules", "cache", style="dashed")
        s.highlight("cache")
        s.highlight("w_cache")
    uml.titles_on_top(s)
    return s


def deployment() -> Scene:
    s = Scene()
    uml.frame(s, "frame", 0, 0, 1080, 440, "deployment", "Orders")
    uml.node(s, "region", 390, 80, 640, 320, "Cloud region", "executionEnvironment")
    uml.node(s, "k8s", 420, 170, 280, 190, "Cluster node")
    uml.artifact(s, "img", 440, 240, 240, 90, "order service image")
    uml.node(s, "pg", 800, 215, 190, 100, "Postgres", "database system", holds=False)
    uml.node(s, "pc", 40, 215, 180, 100, "Customer PC", holds=False)
    s.connect("w_https", "pc", "k8s", "HTTPS", label_size=15)
    s.connect("w_tcp", "k8s", "pg", "TCP", label_size=15)
    uml.titles_on_top(s)
    return s


if __name__ == "__main__":
    components(0).save(HERE / "out" / "uml_components.excalidraw")
    components(1).save(HERE / "out" / "uml_components_v1.excalidraw")
    deployment().save(HERE / "out" / "uml_deployment.excalidraw")
