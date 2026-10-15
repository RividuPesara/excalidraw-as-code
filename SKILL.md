---
name: excalidraw-as-code
description: Draw architecture, system, data-flow, sequence, ER and process diagrams as Excalidraw files by writing a short Python build script against a bundled layout library that routes wires around shapes, keeps labels clear and flags crossings, then render to SVG and PNG and look at the result before showing it. Use when the user asks to draw, diagram, sketch or visualise a system, architecture, flow, pipeline, schema or login sequence, or names Excalidraw.
---

# Excalidraw diagrams as code

A diagram is a small Python **build script**. The script places boxes with
`scripts/excalidraw.py`, declares the wires between them, and on `save()` the library routes
every wire around the shapes, spreads wires that share a side, places each wire label on a
clear straight run, and prints every fault it finds. `scripts/render.py` produces the SVG plus a
temporary PNG preview. You open the preview, judge it and adjust the script until it is clean.

Each diagram leaves three files behind. `system.py` (the script), `system.excalidraw`
(editable at excalidraw.com, wires stay bound to their boxes) and `system.svg` (for docs and
READMEs). A saved PNG only when the user asks for one.

The script is the source of truth. Keep it beside the `.excalidraw` it writes so the next change
is a one-line edit instead of a hunt through generated JSON.

## Setup

- Python 3.9 or newer, nothing to install
- Network access to `https://kroki.io` for SVG, or point `KROKI_URL` at your own Kroki
- Chrome, Edge, Chromium or Firefox for the PNG (found automatically, snap installs work, or set
  `BROWSER_BIN`)
- Optional for icons, a clone of `excalidraw/excalidraw-libraries`. Set `EXCALIDRAW_LIBRARIES`
  to it, or run `python <skill>/scripts/library.py sync` once. Without it items are fetched one
  library at a time from GitHub.

Rendering uploads the scene to Kroki. If the diagram contains names or details the user may not
want leaving the machine, say so first and offer a local Kroki
(`docker run -p 8000:8000 yuzutech/kroki`, then `KROKI_URL=http://localhost:8000`).

## Steps

1. **Collect the pieces.** List 5 to 15 boxes, the wires between them and the groups they
   belong to. For a real codebase, read the code and config first.
2. **Pick the shape of the diagram** from the table below. It decides the layout more than the
   subject does.
3. **Write the script** where the diagram lives, for example `docs/diagrams/system.py`. Put the
   skill's `scripts/` folder on `sys.path`, build a `Scene`, end with `save()`. Copy the closest
   file in `examples/`.
4. **Place boxes.** For flows, create the boxes anywhere, add the wires, then call
   `s.arrange(layers, x, y)` which orders each layer to remove crossings and lines boxes up with
   what feeds them. For hand placed layouts use grid constants
   (`COL = [40, 400, 760]`, `ROW = [220, 410]`). Call `zone_around()` after placing.
5. **Run it.** `save()` prints one `check` line per fault. Clear them all, crossings included.
6. **Render.** `python <skill>/scripts/render.py docs/diagrams/system.excalidraw` writes the SVG
   beside the input and prints the path of a preview PNG. Add `--png` only when the user wants a
   PNG to keep.
7. **Open the preview** image and review it against the list below. Edit, rerun,
   repeat. Expect one to three rounds.
8. **Hand over** the paths of the script, the `.excalidraw` file and the SVG. Point out anything
   drawn as planned rather than built.

For follow-up requests, edit the script and rerun with the same file names.

## Pick the shape

| The idea | Layout | Build with |
|---|---|---|
| request or data path through tiers | layers left to right | `arrange(direction="right")`, zones per tier |
| steps with decisions | layers top to bottom | `arrange(direction="down")`, `shape="diamond"`, yes down, no sideways |
| who calls whom over time | sequence | `sequence()` |
| tables and keys | ER | `table()` and crow's foot heads |
| one thing fans out to many | fan | one box in its own layer, the many in the next |
| many feed one | merge | the many in one layer, the one in the next |
| named products or clouds | icons | `icon()` from a community library |
| sections of a bigger picture | frames | `frame()` around each part |
| UML component, package or deployment view | black and white notation | `scripts/uml.py`, see `examples/uml_views.py` |
| one design shown across versions | a `build(version)` function | the same ids every version, `highlight()` what changed |

## Library at a glance

```python
s = Scene()                                   # the excalidraw look, Scene(style="clean") for crisp lines
top = s.title("Heading", "subtitle")          # returns the y below the title block
s.box(id, x, y, w, h, "Name\ndetail", kind="service", state="built", shape="rectangle")
s.box(id, x, y, label="Auto sized")           # w and h from the text
s.connect(id, src, dst, "label", style="dashed", head="arrow", tail=None)
s.arrange([["a"], ["b", "c"], ["d"]], x, y, direction="right", gap=150, spread=60)
s.zone_around(id, ["b", "c"], "Group", "short note")
s.box(id, x, y, label="Postgres", kind="store", shape="cylinder")
s.highlight(id)                               # pink outline for what a version added
s.save("system.excalidraw")
```

Everything else, with signatures, arrowheads, fonts and icon libraries, is in
`reference.md`. Read it when you need `table`, `sequence`, `icon`, `note`, `frame`, `line`,
`grid`, `legend`, manual `arrow` routes or forced sides.

### kind sets the colour by role

Diagrams look like they were drawn in Excalidraw by default, with rough strokes, the Excalifont
hand drawn face and the shades from the editor's colour picker. `Scene(style="clean")` switches
to straight lines, a plain font and softer tones. Both palettes come from open-color. Every label
clears 12 to 1 contrast on its fill, every outline clears 4 to 1 on white, and kinds that look
alike to colour blind readers are told apart by pattern, outline weight or shape as well.
`python scripts/palette.py` re-checks it after any change.

| kind | role | extra cue |
|---|---|---|
| `entry` | users, browsers, gateways, api processes | |
| `service` | modules, workers, internal components | |
| `store` | databases, buckets, volumes, queues | |
| `outside` | anything run by someone else | hatched by default |
| `gate` | checks, policies, decisions, approvals | use `shape="diamond"` for decisions |
| `focus` | the one element the diagram is about | bold outline |
| `alert` | failure paths, incidents | |
| `plain` | config, supporting or background items | |

Never colour by taste. Two or three kinds carry most diagrams, and one `focus` at most.

### state sets the fill pattern

| state | fill | meaning |
|---|---|---|
| `built` | solid | exists and is ours, the default |
| `external` | hachure | runs outside our control, the default for `outside` |
| `planned` | cross-hatch with a dashed outline | proposed or not built yet |
| `legacy` | zigzag | being retired or replaced |

Add `legend()` whenever more than one state appears.

## Layout rules

- **No crossing wires.** The router detours before it crosses and re-routes any wire that still
  crosses, but it cannot fix a bad order of boxes. When `check` reports a crossing, reorder the
  layers or let `arrange()` order them, swap two boxes in a row, or move the odd box to the outer
  edge. A crossing is a fault, not a style choice.
- **One direction.** Every main-path wire runs the same way, left to right or top to bottom.
  Back edges such as retries are dashed and go around the outside.
- **Spacing.** Layers 150 apart when wires are labelled, 100 when not. Boxes in a layer 40 to 80
  apart, more when wires leave sideways. Wires need room for their label plus about 60.
- **Box size.** Keep boxes in one layer the same size. Let `box()` size itself when unsure.
- **Zones** come from `zone_around()` so their heading never touches a child. In top to bottom
  layouts use `heading="side"` so the heading does not sit where wires come down. Leave 40 or
  more between zones for wires to pass.
- **Reading order.** People and entry points first, storage last, third parties on the outer edge.
- **Wire styles.** Solid for the main request or data path, dashed for async work, jobs and
  config, dotted for loose links such as reads or lookups.
- **Wire labels** one or two words. Longer explanation goes in a zone note or a `note()`.
- **Budget.** Under 30 boxes. Split bigger pictures into frames or several diagrams.

## What check reports

| check line | fix |
|---|---|
| `a and b overlap` or `are closer than 16px` | move them apart or raise `spread` |
| `label of x needs WxH but has WxH` | widen the box, split the line with `\n`, or drop `w` and `h` |
| `wires a and b cross` | reorder boxes as described above |
| `wire w passes through x` | there was no clear path, open a gap or move x |
| `wire w found no clear path` | something blocks its sides, often a zone heading, use `heading="side"` or free the sides |
| `wires a and b share a track` | spread the boxes so each wire gets its own lane |
| `label of w has no straight run long enough` | shorten the label or add space between the boxes |
| `label of w covers ...` or `sits on the border of zone` | add space, or move the label with `arrow(label_at=...)` |
| `label of w will wrap in the editor` | shorten it, Excalidraw wraps arrow labels past that width |
| `text t runs into x` or `sits on the border of zone` | move the text or make the zone with `zone_around()` |
| `x straddles the border of zone z` | include x in the zone or move it out |
| `arrowhead of w is squeezed` | give the last run of the wire 30px or more |

## Diagrams for a report or slide

- A full width diagram shrinks to about half size on an A4 page, so raise the text before
  placing boxes. Set `SIZE["label"]`, `SIZE["note"]` and `SIZE["tiny"]` near the top of the
  script, or pass `size=` and `label_size=`. Nothing under 15 survives the shrink.
- Render with `--png --scale 2` and insert the PNG. Keep the SVG for the web.
- Leave the title and legend out when the document gives the figure a caption, and say what the
  colours or the highlight mean in the text instead.
- Formal documents usually read better with `Scene(style="clean")`.
- For UML views use `uml.py`. It draws in black ink on white, puts the view in a `frame()` with
  its kind and name in the corner tag, and uses `store()` cylinders for databases.
- When one design evolves over iterations, write `build(version)` once, add elements under
  `if version >= n`, and call `s.highlight(id)` on what that version added or changed. Every
  view then keeps its layout and readers spot the change at a glance.

## Reviewing the PNG

- Can you trace the main path in one sentence? If not, the order of boxes is wrong.
- Does every wire run in the reading direction, with back edges dashed around the outside?
- Is any label pressed against a box, a zone edge or an arrowhead?
- Do boxes in a layer share an edge or centre line?
- Does every zone fully wrap its children with room for its heading?
- Is the fill pattern honest? Planned work must not look built.

## Things that bite

- The exporter ignores bindings and draws the stored points, so a wire must start and end on the
  outline. The library does this for rectangles, ellipses and diamonds.
- Excalidraw and Kroki ignore a wire label's own position and draw it on the wire's middle point.
  The library inserts the label point as the middle point so both agree. Plain `label_at` on a
  hand built route works the same way.
- Kroki draws a smaller set of arrowheads than the editor. Only the heads listed in
  `reference.md` render, others raise an error.
- Fonts 1, 2, 3, 5, 6, 8 and 9 render. Text measuring uses widths measured from those fonts.
- Text never wraps on its own. Use `\n`.
- Each element id is used once. A repeat raises an error instead of corrupting the scene.
- Kroki treats a JSON content type as an API envelope and fails. `render.py` posts plain text.
- A wire into a container or zone needs a free gap in front of it. Stacked layers with only a
  zone heading between them give `found no clear path`. Hand route those with `arrow()` and
  `anchor()`.
- Hand routed `arrow()` wires are drawn after the containers they cross and hide their names.
  Call `uml.titles_on_top(s)` before `save()`.
- A ball and socket pair cannot be joined by a routed wire, the shapes are too small. Use
  `uml.assembly()`, which draws the ball sitting in the socket in the gap between components.
- Shapes drawn with depth, such as `uml.node()`, set `_extent` so wires meet the outer edge and
  not the front face. Give any new 3D shape the same.
