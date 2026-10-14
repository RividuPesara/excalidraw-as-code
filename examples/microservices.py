import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import Scene  # noqa: E402

s = Scene()
top = s.title("Shop  ·  Services", "orders flow through a gateway into three services and three stores")
s.legend(40, top + 20, ["built", "external", "planned"])

# boxes start anywhere, arrange() places them in layers once the wires are known
s.box("web", 0, 0, 220, 64, "Web shop\nNext.js", "entry")
s.box("mobile", 0, 0, 220, 64, "Mobile app\niOS and Android", "entry")
s.box("gw", 0, 0, 220, 64, "API gateway\nauth and rate limits", "gate")
s.box("orders", 0, 0, 220, 64, "Orders", "focus")
s.box("catalog", 0, 0, 220, 64, "Catalog", "service")
s.box("pay", 0, 0, 220, 64, "Payments", "service")
s.box("pg", 0, 0, 220, 64, "Postgres\norders and payments", "store")
s.box("search", 0, 0, 220, 64, "Search index", "store", "planned")
s.box("stripe", 0, 0, 220, 64, "Stripe", "outside")

s.connect("w_gw", "web", "gw", "HTTPS")
s.connect("m_gw", "mobile", "gw", "HTTPS")
s.connect("gw_orders", "gw", "orders", "REST")
s.connect("gw_catalog", "gw", "catalog")
s.connect("gw_pay", "gw", "pay")
s.connect("orders_pg", "orders", "pg", "SQL")
s.connect("pay_pg", "pay", "pg", "SQL")
s.connect("catalog_search", "catalog", "search", "index", style="dashed")
s.connect("pay_stripe", "pay", "stripe", "charge")
s.connect("orders_pay", "orders", "pay", "settle", style="dashed")

s.arrange([["web", "mobile"], ["gw"], ["catalog", "orders", "pay"], ["search", "pg", "stripe"]],
          40, top + 140, gap=150, spread=80)
s.zone_around("svc", ["orders", "catalog", "pay"], "Services", "one container each")

s.save(HERE / "out" / "microservices.excalidraw")
