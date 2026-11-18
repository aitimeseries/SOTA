# How references are classified

**In one line:** is the time series an **input** of the AI system, something it infers from or is trained on (→ IEEE P3579), or a **record of the AI system's own operation** (→ IEEE P3998)?

## Q1. IEEE P3579: the AI system consumes external time series

Yes if the reference concerns time series that come from outside an AI system and that are used in one of two ways:

1. **Inference.** The AI system infers from the time series, for example by forecasting, detecting anomalies or classifying. This includes evaluating a model on held-out series.
2. **Training.** The time series becomes training data to build an AI model, including fine-tuning.

This also covers the definition, format, acquisition and preprocessing of such series, even when the reference involves no AI method. Modelling or analysis methods that do not rely on AI are out of scope.

## Q2. IEEE P3998: the AI system produces internal time series

Yes if the reference concerns the time-stamped records that an AI system **produces, or should produce**, about its own operation during its life cycle, and their definition, timing or format. Examples are training logs and metrics, internal states, and inference events. Defining what such a system should produce is the purpose of the standard.

A model's output, such as a forecast or a generated series, is not an internal record. External series, synthetic series and data derived from the internal records are out of scope.

## Where a reference goes

| Q1 | Q2 | Where it goes |
|----|----|---------------|
| yes | no | IEEE P3579 |
| no | yes | IEEE P3998 |
| yes | yes | Both: it appears on the P3579, P3998 **and** joint pages |
| no | no | Not added |

**Examples:**

- Forecasting models and datasets → P3579.
- Explainable AI for time-series classification → P3579.
- Training loggers of reinforcement-learning agents → P3998.
- A date-time or temporal format used both for external data and for internal records, such as ISO 8601 or OWL-Time → both.

## Adding a reference in Zotero

- **P3579 only:** add it to the IEEE-P3579 group.
- **P3998 only:** add it to the IEEE-P3998 group.
- **Both:** add it to one group, then, in Zotero desktop, drag it onto the **same section** of the other group. The joint page is built from the references present in both groups.

File a reference in a section that has no sub-sections. A reference filed on a section with sub-sections, or on no section, is not published.

## Sources

- The scope of [IEEE P3579](https://standards.ieee.org/ieee/3579/11981/).
- The scope of [IEEE P3998](https://standards.ieee.org/ieee/3998/12501/).
