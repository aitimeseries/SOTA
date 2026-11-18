# How references are classified

**In one line:** does the AI system **consume** the time series, as an input it infers from or is trained on (→ IEEE P3579), or **produce** it, as a record of its own operation (→ IEEE P3998)?

## Q1. Is the AI system the consumer? → IEEE P3579

**The AI system consumes the time series:** the series comes from outside the AI system, which uses it in one of two ways.

1. **Inference.** The AI system infers from the time series, for example by forecasting, detecting anomalies or classifying. This includes evaluating a model on held-out series.
2. **Training.** The time series becomes training data to build an AI model, including fine-tuning.

This also covers the definition, format, acquisition and preprocessing of the series an AI system consumes, even when the reference involves no AI method. Modelling or analysis methods that do not rely on AI are out of scope.

## Q2. Is the AI system the producer? → IEEE P3998

**The AI system produces the time series:** the series is a time-stamped record that the AI system **produces, or should produce**, about its own operation during its life cycle. Examples are training logs and metrics, internal states, and inference events. This covers the records and their definition, timing or format. Defining what such a system should produce is the purpose of the standard.

**What "produce" does not cover:** a model's output, such as a forecast or a generated series, is not a record of the AI system's own operation. A forecasting model is therefore a consumer only. External series, synthetic series and data derived from the internal records are out of scope.

## Where a reference goes

| Consumer (Q1) | Producer (Q2) | Where it goes |
|---------------|---------------|---------------|
| yes | no | IEEE P3579 |
| no | yes | IEEE P3998 |
| yes | yes | Both: it appears on the P3579, P3998 **and** joint pages |
| no | no | Not added |

**Examples:**

- Forecasting models and datasets: the AI system consumes the series → P3579.
- Explainable AI for time-series classification: the classifier consumes the series → P3579.
- Training loggers of reinforcement-learning agents: the AI system produces the logs → P3998.
- A date-time or temporal format, such as ISO 8601 or OWL-Time, used both for the series an AI system consumes and for the records it produces → both.

## Adding a reference in Zotero

- **P3579 only:** add it to the IEEE-P3579 group.
- **P3998 only:** add it to the IEEE-P3998 group.
- **Both:** add it to one group, then, in Zotero desktop, drag it onto the **same section** of the other group. The joint page is built from the references present in both groups.

File a reference in a section that has no sub-sections. A reference filed on a section with sub-sections, or on no section, is not published.

## Sources

- The scope of [IEEE P3579](https://standards.ieee.org/ieee/3579/11981/).
- The scope of [IEEE P3998](https://standards.ieee.org/ieee/3998/12501/).
