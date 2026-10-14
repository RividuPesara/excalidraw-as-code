# excalidraw-as-code reference

The full API of `scripts/excalidraw.py`, the arrowheads and fonts that render, and the icon
libraries worth reaching for. `SKILL.md` has the workflow and the layout rules.

## Scene

```python
s = Scene(style="clean", background="#ffffff", font=None)
```

`style="sketch"` switches to rough strokes and the Excalifont hand drawn face. `font` overrides
the face for the whole scene, one of `sans`, `hand`, `code`, `rounded`, `comic`, `virgil`.

## Shapes and text

| call | what it draws |
|---|---|
| `title(heading, subtitle=None, x=40, y=0)` | the heading block, returns the y below it |
| `text(id, x, y, s, size=SIZE["note"], ink="soft", align="left", font=None)` | free text, `x` is the anchor of the alignment |
| `box(id, x, y, w=None, h=None, label="", kind="service", state=None, shape="rectangle", size=17)` | a component, `shape` is `rectangle`, `ellipse` or `diamond`, size comes from the label when `w` or `h` is left out |
| `grid(prefix, labels, x, y, cols, w, h, gap_x=32, gap_y=24, kind=..., state=...)` | boxes in rows, returns their ids |
| `table(id, x, y, name, fields, kind="store", w=None)` | an ER entity with a header band and one field per line |
| `note(id, x, y, s, w=None)` | a sticky note for a remark that is not a component |
| `icon(id, library, item, x, y, size=64, label=None, keep_text=False)` | a community library item scaled into a square with an optional caption |
| `line(id, points, style="solid", color=None, fill=None, width=2)` | an undirected line, a closed polygon when `fill` is given |
| `zone(id, x, y, w, h, title="", note="", kind="plain")` | a dashed group with its heading top left |
| `zone_around(id, ids, title="", note="", pad=32, kind="plain", heading="top")` | a zone sized to wrap the given boxes and its own heading, `heading="side"` puts the heading in a left column so wires can come down into the children |
| `frame(id, x, y, w, h, name="")` | an Excalidraw frame, everything fully inside joins it and is clipped to it |
| `legend(x, y, states=None, kinds=None)` | swatches for fill states and, as a dict of kind to name, colour roles |

`kind` on a zone tints it in the lightest shade of that role, for tiers that belong to one owner.

`SIZE` is `head` 32, `section` 22, `label` 17, `note` 15, `tiny` 13. `ink` is `head`, `body`,
`soft` or any hex colour.

## Wires

| call | what it does |
|---|---|
| `connect(id, src, dst, label=None, style="solid", head="arrow", tail=None, sides=(None, None), elbow=False, width=2)` | a wire routed on save around every shape and free text |
| `arrow(id, points, src=None, dst=None, label=None, style="solid", label_at=None, head="arrow", tail=None, elbow=False)` | a wire on a route you give, for the rare case the router should not decide |
| `sequence(prefix, x, y, actors, messages, gap=240, step=56, kind="service", numbered=True)` | actors with lifelines and one numbered message per row, returns the bottom y |
| `arrange(layers, x, y, direction="right", gap=160, spread=40)` | places the boxes of each layer, orders layers to remove crossings and lines each box up with what feeds it |
| `move(id, x, y)` | moves a box with its label, caption or parts |
| `anchor(id, side, t=0.5)` | a point on the outline for hand built `arrow()` routes |

`sides=("bottom", "top")` pins the side a wire leaves and enters. `None` lets the router pick.
`elbow=True` gives the wire rounded corners and makes the editor re-route it by itself when a box
is dragged.

Messages in `sequence` are `(from, to, label)` or `(from, to, label, style)` where `from` and
`to` are actor names or positions. A message to itself draws a loop.

How routing works. Each wire is first routed alone to pick its sides. Wires that share a side
then get spread ports, ordered by where they turn so neighbours never cross, and a lone wire
between facing sides is lined up to run straight. Wires are routed again in order on a grid of
gaps between shapes, paying for length, bends, crossings and shared tracks, so a short detour
always wins over a crossing. Any wire that still crosses is torn up and routed against all the
others. Diamonds and ellipses give each wire its own vertex.

## Arrowheads

Only these render through Kroki. The editor draws a few more, which fall back to a plain arrow in
the export, so the library refuses them.

| head | use for |
|---|---|
| `arrow` | flow, the default |
| `triangle` and `triangle_outline` | UML inheritance and realisation |
| `diamond` and `diamond_outline` | UML composition and aggregation |
| `circle` and `circle_outline` | endpoints, events, optional ends |
| `bar` | a hard stop or a terminator |
| `one`, `many`, `one_or_many` | ER cardinality, written as the crow's foot heads the editor upgrades on open |

Set `tail` for a head on the start. `head=None` makes a plain connector.

## Fonts

| font | family | look |
|---|---|---|
| `sans` | 2 Helvetica | the default, clean |
| `hand` | 5 Excalifont | the current hand drawn face, used by `style="sketch"` |
| `virgil` | 1 Virgil | the older hand drawn face |
| `code` | 3 Cascadia | monospace for code and identifiers |
| `rounded` | 6 Nunito | soft and friendly |
| `comic` | 8 Comic Shanns | monospace with a hand feel |

Family 10 falls back to a serif in the export and is not offered.

## Icons

```bash
python scripts/library.py search kafka              # items whose name matches, across every library
python scripts/library.py items lowess/kubernetes-icons-set.excalidrawlib
python scripts/library.py sheet lowess/kubernetes-icons-set.excalidrawlib -o /tmp/k8s.excalidraw
python scripts/render.py /tmp/k8s.excalidraw        # look at the numbered contact sheet
python scripts/library.py sync                       # clone the library repo for item search
```

Then `s.icon("pod", "lowess/kubernetes-icons-set.excalidrawlib", "pod", x, y, 64, "upload pods")`.
`item` is an index or a name. Library text is dropped unless `keep_text=True`, so give a
`label` instead. Wires bind to an invisible box around the icon.

Use icons for products a reader recognises by logo, and plain boxes for your own components.
Keep one icon size per diagram.

These libraries were checked to import cleanly.

| library | covers |
|---|---|
| `childishgirl/aws-architecture-icons.excalidrawlib` | 249 AWS services |
| `stojanovic/aws-serverless-icons-v2.excalidrawlib` | AWS serverless |
| `mguidoti/original-google-architecture-icons.excalidrawlib` | 139 Google Cloud services |
| `rockssk/microsoft-azure-cloud-icons.excalidrawlib` | common Azure services |
| `7demonsrising/azure-compute.excalidrawlib` | Azure compute, with sister libraries for network, storage and containers |
| `boemska-nik/kubernetes-icons.excalidrawlib` | 74 Kubernetes objects |
| `lowess/kubernetes-icons-set.excalidrawlib` | a smaller Kubernetes set |
| `dwelle/network-topology-icons.excalidrawlib` | routers, switches, firewalls |
| `samu_x86/network-elements.excalidrawlib` | load balancer and other network gear |
| `mateuszbaransanok/it-icons.excalidrawlib` | generic servers, users, devices |
| `pclainchard/it-logos.excalidrawlib` | tech logos such as Kafka and Docker |
| `anna-pastushko/architecture-diagram-components.excalidrawlib` | users, clients, generic components |
| `chuqbach/data-platform.excalidrawlib` | data tools such as Spark and Airflow |
| `stuc2010/enterprise-integration-patterns.excalidrawlib` | messaging patterns |
| `dmitry-burnyshev/c4-architecture.excalidrawlib` | C4 model shapes |
| `BjoernKW/UML-ER-library.excalidrawlib` | UML and ER shapes |

## Palette

`scripts/palette.py` holds `TONES` as kind to fill, outline and hatch, all open-color values.
Running it prints the contrast of each kind and fails if a label drops under 4.5 to 1, an
outline under 3 to 1, or two kinds become indistinguishable under deuteranopia, protanopia or
tritanopia. Re-run it after changing any colour, for example to a brand palette.
