# Synoptic diagrams

A synoptic is a hand-made (or generated) overview picture of the grid, shown in the argus **Synoptic** window. The argus backends (GM and SCADA) render it to SVG with the current values of their network model at each request; argus refreshes it every 2 s.

## Configuration

In the session `config.toml`:

```toml
[input_files.argus]
synoptics_dir = "synoptics"  # relative to the config.toml
```

The directory holds one JSON file per synoptic, listed in `index.json` (e.g. `["nordic.json"]`).

Endpoints: `GET /synoptics` → `[{name, title}]`, `GET /synoptic/{name}` → `{name, title, svg}`.

## Generators

- `iidm_to_synoptic.py`: from a network file (geographical layout when every substation has a `substationPosition`, force-directed layout otherwise). Example:
  `uv run --project tools/synoptic python tools/synoptic/iidm_to_synoptic.py docs/orchestrator/examples/Nordic/Nordic.xiidm --outputs docs/orchestrator/examples/Nordic/game_master_outputs.json --out docs/orchestrator/examples/Nordic/synoptics --name nordic --title "Nordic 32"`
  (from `Twin-CR/`; `--outputs` adds the frequency (not present in iidm), from the `OmegaRef` output).
- `synoptic_lib.py`: helpers (network reader: pypowsybl into small dataclasses, element builders, expressions) for other generators, e.g. converters of existing SCADA pictures.

## Format (`twincr-synoptic/1`)

```json
{
 "format": "twincr-synoptic/1", "name": "nordic", "title": "Nordic 32",
 "width": 1800, "height": 1200, "background": "#1c3f41", "locale": "fr", "fontSize": 14,
 "palette": {"nodes": ["#ff2a2a", "#e8e8e8", "#38d038", "#ffb000"], "off": "#6f8586", "unknown": "#b08cd8",
             "text": "#ffffff", "value": "#ff3030", "unitOn": "#4a6cf0", "arrow": "#ffffff"},
 "elements": [ ... ]
}
```

`palette.nodes[i]` is the color of the electrical node `i` of a voltage level: its electrical nodes (bus view buses with at least one connected terminal) are numbered per voltage level by decreasing number of connected terminals (ties by bus id), so 0 is its main node and colors stay stable between refreshes (colors repeat when there are more nodes than colors). `off` is used for disconnected / de-energized objects and `unknown` for ids not found in the network. `locale` drives the decimal separator of the values.

All elements take `x`, `y` (SVG user units, y downwards) and optionally `id`, `tooltip` and `equipment`: the network equipment shown (default: `branch` / `vl`). It is the target of the argus context menu (properties, add to chart) and of the hover card (properties from the network tables, e.g. `energy_source` / `max_p` of a generator); the tooltip defaults to it.

| type | fields | rendering |
|---|---|---|
| `node` | `vl`, `r` | voltage level circle; the number of electrical nodes is written inside when > 1, `?` when the id is unknown |
| `branch` | `branch`, `points` `[[x, y], ...]`, `side1` (1 or 2: network side of the first point), `width` | polyline, each half colored with the electrical node of its end (dashed when disconnected) |
| `arrow` | `angle` (deg, direction of a positive `dir`), `dir` (expr), `deadband`, `size`, `fill`, `expr`, `format`, `labelDx`, `labelDy`, `thresholds` | arrow pointing along `angle` if `dir` > `deadband`, opposite if `dir` < `-deadband`, hidden otherwise; optional label (absolute value of `expr`) |
| `unit` | `on` (expr), `r`, `label` | generating unit: filled when `on` ≠ 0, empty when 0, dashed when unknown |
| `value` | `expr`, `format` (printf, default `%.0f`), `prefix`, `suffix`, `fill`, `fontSize`, `anchor`, `thresholds` | text of the value, `?` when unknown |
| `text` | `text`, `fill`, `fontSize`, `anchor` (`start`/`middle`/`end`), `bold`, `italic` | static text |
| `table` | `rows` `[{label, expr \| text, format, prefix, suffix}]`, `title`, `labelWidth`, `valueWidth`, `rowHeight`, `fontSize`, `labelFill`, `valueFill`, `fill`, `stroke` | framed label / value table |
| `rect`, `polyline` | `w`, `h`, `rx` / `points`, `stroke`, `fill`, `width`, `dash` | decoration |

`thresholds`: `[{"value": 9, "fill": "#ffb000"}, {"value": 10, "fill": "#ff3030"}]` (ascending) colors a value.

### Expressions

`expr`, `dir` and `on` are expressions: numbers, `+ - * / %`, comparisons, `&& || !`, and the functions below. Ids are quoted (`'...'` or `"..."`). An unknown id, a missing value or a division by zero gives NaN, displayed `?` (propagated through the operators; `coalesce(a, b, ...)` returns the first known argument).

| function | value |
|---|---|
| `p1/p2/q1/q2/i1/i2('branchId')` (`p3`, `q3`, `i3` for 3 windings transformers) | side values of a line, transformer, tie line or HVDC line (0 if the side is disconnected) |
| `p/q/i('injectionId')`, `pgen('genId')` | injection values (load sign convention), `pgen` = -p |
| `ilim1/ilim2('branchId')` | permanent current limit of a side |
| `connected('id')` | 1 if all the terminals (or the switch) are closed / connected |
| `v/vmax/vmin('vlId')`, `nbus('vlId')` | bus voltages (kV) and number of electrical nodes of a voltage level |
| `bus/bus1/bus2('id')` | index of the electrical node of a terminal in its voltage level |
| `targetp/maxp/minp('genId')` | generator set point and limits |
| `exchange('FR', 'BE')` | active power from country A to country B on the lines / HVDC between them |
| `out('id')` | latest raw telemetry value: gm_output / scada_output id, TI libelle or tase2 id, e.g. the frequency (Hz) `out('OmegaRef_omegaRef_0_value')` (Nordic; the id depends on the Dynawo model name, see `synoptic_lib.output_ids_by_kind`). In GM, the topic of the output is subscribed automatically |
| `abs round floor ceil sqrt sign min max sum if(c, a, b) coalesce isnan nan` | math |

`round(x, step)` rounds to a multiple of `step`. Example, loading of a line in deciles of its permanent limit:
`round(10*coalesce(max(abs(i1('L1'))/ilim1('L1'), abs(i2('L1'))/ilim2('L1')), abs(i1('L1'))/ilim1('L1')))`.
