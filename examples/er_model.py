import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from excalidraw import Scene  # noqa: E402

s = Scene()
top = s.title("Shop  ·  Data model", "crow's foot ends show how many rows sit on each side")

s.table("customer", 40, top + 60, "customer", ["id  uuid", "email  text", "created_at  timestamptz"])
s.table("order", 420, top + 60, "order", ["id  uuid", "customer_id  uuid", "status  text", "total  numeric"])
s.table("item", 800, top + 60, "order_item", ["order_id  uuid", "product_id  uuid", "qty  int"])
s.table("product", 800, top + 300, "product", ["id  uuid", "name  text", "price  numeric"], kind="service")

s.connect("c_o", "customer", "order", "places", head="many", tail="one")
s.connect("o_i", "order", "item", "contains", head="one_or_many", tail="one")
s.connect("p_i", "product", "item", head="many", tail="one")

s.save(HERE / "out" / "er_model.excalidraw")
