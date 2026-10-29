# Review artifact design system

The template carries these tokens and components verbatim. Extend, do not restyle.

## Tokens

Light is the default. Dark is an override block on `html[data-theme="dark"]`, flipped by the header
toggle; the choice persists in `localStorage` under `review-artifact-theme`. Never hardcode a colour
in a rule — every value comes from a token, so the two themes stay in step.

```css
/* light (default) */
--bg:#f5f7fb  --panel:#ffffff  --panel2:#f4f7fc  --line:#dde4ef
--txt:#0f172a  --txt2:#334155  --dim:#5a6b85  --dim2:#8496b1
--add:#059669  --mod:#b45309  --del:#dc2626  --new:#7c3aed  --cyan:#0891b2

/* dark */
--bg:#070b14  --panel:#101828  --panel2:#0c1424  --line:#1c2942
--txt:#e6edf7  --txt2:#cbd5e1  --dim:#8ba0bd  --dim2:#5f7290
--add:#34d399  --mod:#fbbf24  --del:#f87171  --new:#a78bfa  --cyan:#22d3ee
```

Semantics: green = added, amber = modified, rose = deleted, violet = second direction or carried-in
work, cyan = structure (section numbers, connectors, primary button). In light mode the "-fg" tokens
are darker than the base so text on a white panel still passes contrast; never use `--add` for body
text.

Every panel is a two-stop gradient over `--panel2`. Borders are 1px `--line`; hover lifts 3–4px and
swaps the border to the panel's accent at ~40% alpha via `color-mix`. The theme switch transitions
background and text over 250ms; everything else stays put.

## Type

- UI: system sans stack, base 16px. Headings `font-weight:750–800`, `letter-spacing:-.015em`.
- Machine text: the mono stack — table names, function signatures, paths, event names. Never mono
  for prose.
- **Floor: 14.5px.** Table types, tree rows, badges, legends, hints, footers — nothing smaller.
  Solving an overflow by shrinking type is the wrong fix; cut text or widen the element.
- Section headers: `NN` chip in cyan mono + `h2`. Section subtitles cap at one line.
- Vietnamese prose is fully diacritic; do not strip accents to fit a card.

## Components

| Component | Use | Notes |
|---|---|---|
| `.stat` | headline counts | counter animates once; label uppercase 11px |
| `.ws` | one workstream card | left stripe cyan for the artifact's own subject, violet for carried work |
| `.node` + `.conn` | flow stage and link | 132px nodes, 26px connectors; `SỬA`/`MỚI` badge on the corner |
| `.fc-stage` | **BA flowchart** | 1020×1080 SVG: stadium start/end, `polygon` diamonds for decisions, `.n-err` terminals on every "không" branch, `.n-ok` for the write steps |
| `.fc-edge` | flowchart arrow | `stroke-dashoffset` draw-in; `.happy` cyan for the valid path, default grey for refusals, `.stale` amber for "no change but event still fires" |
| `.merge` | rule outcome table | three columns: what arrives, the effect verb, the resulting row; colour the row by verb |
| `.erd-wrap` `.erd-stage` | **the visual schema** | fixed 1080×730 stage scaled with `--s`; absolutely positioned `.e-box` cards over an SVG `.wires` layer |
| `.e-box` | one table in the ERD | `.eh` header with `.est` status chip, `.e-row` columns, `.e-note` for one caveat |
| `.e-row.added/.changed` | column delta | green `+` or amber `~`, left stripe, tinted row |
| `.wires path` | relation line | `stroke-dashoffset` draw-in on reveal; `.emph` for the second relation |
| `.fn3` | function groups | new / replaced / dropped, three columns under the ERD |
| `.tbl` `.col` | table card | legacy flat list; prefer the ERD for anything with relations |
| `.rule` | constraint or behaviour note | block flow, violet left border, inline `code` allowed |
| `.fnrow` | function add/replace/drop | `.added` `.changed` `.dropped` left stripe; sig in dim mono |
| `.ev` | event row | `IN`/`OUT` chip then name, version pushed right |
| `.err` | error code | `.add` for new, `.rm` strikes the code |
| `.verchain` | version path | last chip filled cyan |
| `.area` | per-area bars | green add + red delete on one track, file count right |
| `.tree` | folder tree | collapsible, status dot per file, `+/−` per file |
| `.rev` | finding | severity chip `CHẶN` / `NÊN XEM` / `GHI NHẬN` |

## Animation inventory

| Effect | Where | Duration |
|---|---|---|
| `pulse` | eyebrow dot | 2.2s loop |
| `march` | connector dashes | 1.1s linear loop |
| counter ease-out | stat values | 1.1s, once |
| bar width | area chart | 1.1s, on reveal |
| `slideIn` | diff replay | 0.45s, 90ms stagger |
| tree open | `max-height` + opacity | 0.32s |
| reveal | sections on scroll | 0.6s |

Reduced motion kills all of them; the content must stay complete without motion.

## Anti-patterns

- Rainbow: more than four semantic colours and none of them means anything.
- Colour as the only signal — always pair with a mark (`+`, `−`, `~`), a strike, or a word.
- A flow diagram with equal-weight boxes and no badges: the reader cannot tell which stage is new.
- Burying a deletion. Dropped objects are the highest-signal part of most diffs.
- Long paragraphs inside the artifact. If it needs explaining, explain it in chat.
- Asserting behaviour the diff does not show. Mark inference as inference.
- Screenshotting something you did not open. Render it, look at it, then report.
