---
name: excalidraw-as-code
description: Draw architecture, system, data-flow and process diagrams as Excalidraw files by writing a short Python build script against a bundled layout library, then render to SVG and PNG and look at the result before showing it. Use when the user asks to draw, diagram, sketch or visualise a system, architecture, flow or pipeline, or names Excalidraw.
---

# Excalidraw diagrams as code

A diagram is a small Python **build script**. The script places every element on a planned
grid with `scripts/excalidraw.py`, which also routes wires between shape edges and reports
layout faults. `scripts/render.py` produces the SVG plus a temporary PNG preview. You open the
preview, judge it and adjust the script until it reads cleanly.

Each diagram leaves three files behind. `system.py` (the script), `system.excalidraw`
(editable at excalidraw.com) and `system.svg` (for docs and READMEs). A saved PNG only when
the user asks for one.

The script is the source of truth. Keep it in the repo beside the `.excalidraw` it writes, so
the next change is a one-line edit instead of a hunt through generated JSON.

## Setup

- Python 3.9 or newer, nothing to install
- Network access to `https://kroki.io` for SVG, or point `KROKI_URL` at your own Kroki
- Chrome, Edge or Chromium for the PNG (found automatically, or set `BROWSER_BIN`)

Rendering uploads the scene to Kroki. If the diagram contains names or details the user may
not want leaving the machine, say so first and offer a local Kroki
(`docker run -p 8000:8000 yuzutech/kroki`, then `KROKI_URL=http://localhost:8000`).

## Steps

1. **Collect the pieces.** List 5 to 15 boxes and the groups they belong to (tiers,
   containers, owners). For a real codebase, read the code and config first.
2. **Plan the grid on paper.** Write the column x values and row y values as constants at the
   top of the script (`COL = [40, 400, 800]`, `ROW = [220, 410]`). Every box snaps to them.
3. **Write the script** where the diagram lives, for example `docs/diagrams/system.py`. Put
   the skill's `scripts/` folder on `sys.path`, build a `Scene`, end with `save()`.
   `examples/web_app.py` is a ready template.
4. **Run it.** `save()` prints every overlap, every label that won't fit its box and every
   wire that stops inside a shape. Clear them all.
5. **Render.** `python <skill>/scripts/render.py docs/diagrams/system.excalidraw` writes the
   SVG beside the input and prints the path of a preview PNG in the temp folder. Add `--png`
   only when the user wants a PNG to keep, for slides or chat.
6. **Open the preview** with the Read tool and review it against the list below. Edit, rerun,
   repeat. Expect two or three rounds.
7. **Hand over** the paths of the script, the `.excalidraw` file and the SVG. Point out
   anything drawn as planned rather than built.

For follow-up requests, edit the script and rerun with the same file names. For an
alternative version, copy the script under a new name.

## Library

```python
s = Scene()
s.text(id, x, y, "Heading", SIZE["head"], "head")           # free text, break lines with \n
s.box(id, x, y, w, h, "Name\ndetail", kind="service", state="built")
s.zone(id, x, y, w, h, "Group", "short note")                # dashed group, heading top left
s.grid("m", ["A", "B", "C", "D"], x, y, cols=2, w=240, h=60)  # boxes in rows, returns ids
s.connect(id, src, dst, "label", style="dashed")             # wire between edges, straight or L
s.arrow(id, [(x1, y1), (x2, y1), (x2, y2)], src, dst, "label", label_at=(x, y))
s.anchor(id, "bottom", t=0.3)                                # a point on an edge for arrow()
s.legend(x, y, ["built", "external", "planned"])            # swatches for the states shown
s.save("system.excalidraw")
```

### kind sets the colour by role

| kind | role |
|---|---|
| `entry` | users, browsers, gateways, api processes |
| `service` | modules, workers, internal components |
| `store` | databases, buckets, volumes, queues |
| `outside` | anything run by someone else |
| `gate` | checks, policies, decisions, approvals |
| `focus` | the one element the diagram is about |
| `alert` | failure paths, incidents |
| `plain` | config, supporting or background items |

### state sets the fill pattern

Excalidraw has four fill styles. Each one has a fixed meaning here, so a reader can tell what
exists today at a glance:

| state | fill | meaning |
|---|---|---|
| `built` | solid | exists and is ours, the default |
| `external` | hachure | runs outside our control, the default for `outside` |
| `planned` | cross-hatch with a dashed outline | proposed or not built yet |
| `legacy` | zigzag | being retired or replaced |

Hatched boxes use a stronger tone so the lines show, and the label stays readable on top.
Add `legend()` whenever more than one state appears.

### Text sizes

`SIZE` holds the scale. `head` 32 for the diagram title, `section` 22 for zone headings,
`label` 17 inside boxes, `note` 15 for subtitles and zone notes, `tiny` 13 for wire labels and
the legend.

## Layout

- **Box size** comes from the longest line, roughly `characters × size × 0.55 + 30` wide, and
  56 to 70 tall for two lines. Keep boxes in one row or column identical.
- **Column pitch** about 360 to 400 for 240-wide boxes, which leaves 120 for a labelled wire.
  Unlabelled wires need about 80. Shapes in a grid keep at least 24 apart.
- **Zones** pad their children by about 40 and reserve about 90 at the top for the heading
  and note.
- **Reading order** goes left to right or top to bottom. People and entry points first,
  storage last, third parties on the outer edge.
- **Lanes.** Leave an empty band of 40 to 60 between rows of zones. Wires that need to cross
  the diagram travel in these lanes.
- **Steps in a sequence** get numbers in their labels (`1 Sign in`, `2 Check`) and short wires
  between them.
- **Wire styles.** Solid for the main request or data path, dashed for async work, jobs and
  config, dotted for loose links such as reads or lookups.
- **Wire labels** stay at one or two words. Longer explanation belongs in a zone note.
- **Budget.** Under 30 boxes. One `focus` box at most.

## Reviewing the PNG

- Can you trace the main path in one sentence ("the browser calls the API, which writes to
  Postgres")? If not, the flow needs a clearer direction or fewer crossings.
- Does any wire pass over a box it is not attached to? Route it through a lane with `arrow()`.
- Is any label cut off or pressed against an edge? Widen the box or split the line.
- Is a wire label sitting on a zone border or hiding an arrowhead? Move it with `label_at`.
- Do the boxes in a row share a top edge? Use the grid constants instead of loose numbers.
- Does every zone fully wrap its children with room for its heading?
- Is the fill pattern honest? Planned work must not look built.

## Things that bite

- Excalidraw's exporter ignores bindings and draws the stored points as they are. A wire must
  start and end on the outline itself, which `connect()` and `anchor()` take care of.
- A bound wire label blanks out the wire behind its whole text box. The library keeps that box
  as narrow as the words.
- Text never wraps on its own. Use `\n`.
- Each element id is used once. A repeat raises an error instead of silently corrupting the
  scene.
- Kroki treats a JSON content type as an API envelope and fails. `render.py` posts the scene
  as plain text.
