# State of the Art — IEEE P3998

## STANDARDS

_No references yet._

## RESOURCES

### Datasets

_No references yet._

### Frameworks

_No references yet._

### Algorithms

| Authors | Title | Year | DOI | Notes |
|---------|-------|------|-----|-------|
| — | <span id="ref-Z6TDV2T2">[A2C — Logger — Stable Baselines3 2.8.0a4 documentation](https://stable-baselines3.readthedocs.io/en/master/modules/a2c.html#stable_baselines3.a2c.A2C.logger)</span> |  |  | <a href="#note-Z6TDV2T2">📝</a> |
| — | <span id="ref-FCNVJ24Q">[PPO — Logger — Stable Baselines3 2.8.0a4 documentation](https://stable-baselines3.readthedocs.io/en/master/common/logger.html)</span> |  |  | <a href="#note-FCNVJ24Q">📝</a> |

<details id="note-Z6TDV2T2">
<summary>💬 <b>A2C — Logger — Stable Baselines3 2.8.0a4 documentation</b> — Any AIS, during its lifecycle, produces temporally ordered data as a byproduct…</summary>

<p>Any AIS, during its lifecycle, produces temporally ordered data as a byproduct of its operation. As a concrete illustration, the Proximal Policy Optimization (PPO) implementation in Stable-Baselines3 (SB3) includes a built-in logger that records, at each logging interval, a single snapshot grouping training metrics (loss, policy divergence), rollout statistics (mean reward, episode length), and temporal markers (iterations, elapsed time, total timesteps).
These repeated snapshots form ordered sequences of values produced internally by the system, not consumed from an external source.
However, these temporal markers remain relative counters and durations — not standardized timestamps. There is no formal temporal reference framework governing how these internal records are indexed, formatted, or exchanged. This is precisely the gap P3998 aims to address: defining a unified format for the temporal data records that AIS inherently produce but do not yet record in a standardized way.
P3579 standardizes how AIS consume external time series; P3998 addresses the complementary direction — the internal temporal data records that AIS produce. Together, they cover both sides of the relationship between AIS and time series.</p>
<p><em>— jschneerson, 2026-03-26</em> · <a href="#ref-Z6TDV2T2">↩ back to reference</a></p>

</details>

<details id="note-FCNVJ24Q">
<summary>💬 <b>PPO — Logger — Stable Baselines3 2.8.0a4 documentation</b> — Any AIS, during its lifecycle, produces temporally ordered data as a byproduct…</summary>

<p>Any AIS, during its lifecycle, produces temporally ordered data as a byproduct of its operation. As a concrete illustration, the Proximal Policy Optimization (PPO) implementation in Stable-Baselines3 (SB3) includes a built-in logger that records, at each logging interval, a single snapshot grouping training metrics (loss, policy divergence), rollout statistics (mean reward, episode length), and temporal markers (iterations, elapsed time, total timesteps).
These repeated snapshots form ordered sequences of values produced internally by the system, not consumed from an external source.
However, these temporal markers remain relative counters and durations — not standardized timestamps. There is no formal temporal reference framework governing how these internal records are indexed, formatted, or exchanged. This is precisely the gap P3998 aims to address: defining a unified format for the temporal data records that AIS inherently produce but do not yet record in a standardized way.
P3579 standardizes how AIS consume external time series; P3998 addresses the complementary direction — the internal temporal data records that AIS produce. Together, they cover both sides of the relationship between AIS and time series.</p>
<p><em>— jschneerson, 2026-03-26</em> · <a href="#ref-FCNVJ24Q">↩ back to reference</a></p>

</details>

## PUBLICATIONS

### Reports

_No references yet._

### Patents

_No references yet._

### Papers

_No references yet._


---

## Contributors

*The following members have contributed references to this library:*

- [jschneerson](https://www.zotero.org/jschneerson)

