# State of the Art — IEEE P3579

*See also the [references common to P3579 and P3998](../p3579-p3998/index.md).*

## PUBLICATIONS

### Papers

| Authors | Title | Year | DOI | Notes |
|---------|-------|------|-----|-------|
| Wang | <span id="ref-7AH99IWN">[Artificial Intelligence Algorithm for Optimal Time Series Data Model](https://ieeexplore.ieee.org/document/9039604)</span> | 2025 | 10.1109/ACCESS.2020.2981488 | — |
| Theissler, Spinnato, Schlegel, Guidotti | <span id="ref-NJNFHFNK">[Explainable AI for Time Series Classification: A Review, Taxonomy and Research Directions](https://ieeexplore.ieee.org/document/9895252)</span> | 2022 | 10.1109/ACCESS.2022.3207765 | — |
| Lim, Zohren | <span id="ref-4Q3UIAIE">[Time Series Forecasting With Deep Learning: A Survey](http://arxiv.org/abs/2004.13408)</span> | 2021 | 10.1098/rsta.2020.0209 | — |

### Patents

_No references yet._

### Reports

_No references yet._

## RESOURCES

### Algorithms

| Authors | Title | Year | DOI | Notes |
|---------|-------|------|-----|-------|
| — | <span id="ref-D8E8FJST">[A2C — Logger — Stable Baselines3 2.8.0a4 documentation](https://stable-baselines3.readthedocs.io/en/master/modules/a2c.html#stable_baselines3.a2c.A2C.logger)</span> |  |  | <a href="#note-D8E8FJST">📝</a> |

<details id="note-D8E8FJST">
<summary>💬 <b>A2C — Logger — Stable Baselines3 2.8.0a4 documentation</b> — Any AIS, during its lifecycle, produces temporally ordered data as a byproduct…</summary>

<p>Any AIS, during its lifecycle, produces temporally ordered data as a byproduct of its operation. As a concrete illustration, the Proximal Policy Optimization (PPO) implementation in Stable-Baselines3 (SB3) includes a built-in logger that records, at each logging interval, a single snapshot grouping training metrics (loss, policy divergence), rollout statistics (mean reward, episode length), and temporal markers (iterations, elapsed time, total timesteps).
These repeated snapshots form ordered sequences of values produced internally by the system, not consumed from an external source.
However, these temporal markers remain relative counters and durations — not standardized timestamps. There is no formal temporal reference framework governing how these internal records are indexed, formatted, or exchanged. This is precisely the gap P3998 aims to address: defining a unified format for the temporal data records that AIS inherently produce but do not yet record in a standardized way.
P3579 standardizes how AIS consume external time series; P3998 addresses the complementary direction — the internal temporal data records that AIS produce. Together, they cover both sides of the relationship between AIS and time series.</p>
<p><em>— jschneerson, 2026-11-18</em> · <a href="#ref-D8E8FJST">↩ back to reference</a></p>

</details>

### Datasets

| Authors | Title | Year | DOI | Notes |
|---------|-------|------|-----|-------|
| — | <span id="ref-6CB8RX6D">[Chronos Models & Datasets - a amazon Collection](https://huggingface.co/collections/amazon/chronos-models-and-datasets)</span> | 2025 |  | — |

### Frameworks

_No references yet._

### Models

| Authors | Title | Year | DOI | Notes |
|---------|-------|------|-----|-------|
| — | <span id="ref-UGU54QGJ">[Time Series Forecasting Models – Hugging Face](https://huggingface.co/models)</span> | 2026 |  | — |
| — | <span>[Chronos Models & Datasets - a amazon Collection](https://huggingface.co/collections/amazon/chronos-models-and-datasets)</span> | 2025 |  | — |

## STANDARDS

_No references yet._


---

## Contributors

*The following members have contributed references to this library:*

- [jschneerson](https://www.zotero.org/jschneerson)

