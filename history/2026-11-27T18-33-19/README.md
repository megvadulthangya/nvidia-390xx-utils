# Harvest Index — 2026-11-27 18:33:19 

## TL;DR

- **State:** ❗0 failed · 🔍0 suspicious · ⚠6 warnings · ✅4 clean · 🚫0 not-built
- **Action needed (2):**
    - 6 builds · 6 hits · `warning: no previous prototype for 'nvidia_wq_flush' [-Wmissing-prototypes]`
    - 6 builds · 6 hits · `warning: no previous prototype for 'nvidia_wq_queue' [-Wmissing-prototypes]`
- **Since last run (`2026-11-27T15-55-46`):** ✅0 resolved · 🆕2 new · 🔀6 status changes

## 📊 Changes since 2026-11-27T15-55-46

### ✅ Resolved signatures (0)

_None._

### 🆕 New signatures (2)

- `warning: no previous prototype for 'nvidia_wq_flush' [-Wmissing-prototypes]`
- `warning: no previous prototype for 'nvidia_wq_queue' [-Wmissing-prototypes]`

### 🔀 Status changes (6)

- `390xx/normal/linux-next-nvidia-390xx`: ✅ clean → ⚠ warnings
- `390xx/normal/linux612-nvidia-390xx`: ✅ clean → ⚠ warnings
- `390xx/normal/linux618-nvidia-390xx`: ✅ clean → ⚠ warnings
- `390xx/normal/linux73-nvidia-390xx`: ✅ clean → ⚠ warnings
- `390xx/normal/linux74-nvidia-390xx`: ✅ clean → ⚠ warnings
- `390xx/rt/linux612-rt-nvidia-390xx`: ✅ clean → ⚠ warnings


## Overview

- **Diag root:** `/build/sources`
- **Harvest:**   `/build/harvest`
- **Branches:**  390xx
- **Builds:** 10 — ❗0 failed, 🔍0 suspicious, ⚠6 warn, ✅4 clean, 🚫0 not-built
- **Warning signatures:** 2 total — 2 actionable across multiple builds, 0 informational, 0 unique to one build
- **Suspicious signatures:** 0  ·  **integrity issues:** 0 builds  ·  **integrity notes:** 0 builds

## Legend

| Symbol | Status | Meaning |
|:------:|--------|---------|
| ❗ | failed     | make.log contains real errors — **blocker** |
| 🔍 | suspicious | no errors, but suspicious lines or integrity issues |
| ⚠  | warnings   | built, no errors, non-noise warnings to review |
| ✅ | clean      | built, no errors, only known noise |
| 🚫 | not-built  | no make.log at all |
| 🧪 | utils      | userspace utils failure, mpatch debug archived |

Per-build detail lives in the harvest tree, one directory per kernel: `00-header.txt`, `01-errors.txt`, `02-warnings.txt`, `03-noise.txt`, `04-suspicious.txt`, `summary.txt`.

The raw `make.log` is also archived in every build directory as `make.log.zst` (or `.gz` / plain).

## Status table

| # | Branch | Variant | Kernel | Driver | Status | Err | Clean (uniq/total) | Susp | Noise | Integ |
|---|--------|---------|--------|--------|:------:|----:|-------------------:|-----:|------:|:-----:|
| 1 | 390xx | normal | 6.1.192-2-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 164942 |  |
| 2 | 390xx | normal | 6.12.117-1-MANJARO | 390.157 | ⚠ warnings | 0 | 2 / 2 | 0 | 94474 |  |
| 3 | 390xx | normal | 6.18.63-3-MANJARO | 390.157 | ⚠ warnings | 0 | 2 / 2 | 0 | 94474 |  |
| 4 | 390xx | normal | 6.6.162-2-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 5 | 390xx | normal | 7.3.4-3-MANJARO | 390.157 | ⚠ warnings | 0 | 2 / 2 | 0 | 94474 |  |
| 6 | 390xx | normal | 7.4.0-rc2-3-MANJARO | 390.157 | ⚠ warnings | 0 | 2 / 2 | 0 | 94474 |  |
| 7 | 390xx | normal | 7.4.0-rc4-next-20261124-1-MANJARO | 390.157 | ⚠ warnings | 0 | 2 / 2 | 0 | 94474 |  |
| 8 | 390xx | rt | 6.1.190-2-rt70-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 164942 |  |
| 9 | 390xx | rt | 6.12.116-1-rt22-MANJARO | 390.157 | ⚠ warnings | 0 | 2 / 2 | 0 | 94474 |  |
| 10 | 390xx | rt | 6.6.159-2-rt82-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |

## 🔁 Cross-build warning signatures

Warnings appearing in **more than one build**. Fixing the top signature fixes the most builds at once.

### 🎯 Actionable (driver source)

| # | Builds | Hits | Signature | Branches |
|---|-------:|-----:|-----------|----------|
| 1 | 6 | 6 | `warning: no previous prototype for 'nvidia_wq_flush' [-Wmissing-prototypes]` | 390xx/normal, 390xx/rt |
| 2 | 6 | 6 | `warning: no previous prototype for 'nvidia_wq_queue' [-Wmissing-prototypes]` | 390xx/normal, 390xx/rt |

### ⚙️ Informational (build system / Makefile)

_None._

## 🧩 Unique to one build

Warnings in exactly **one** build. Usually kernel- or config-specific.

_No unique-to-one-build warnings._

---
_End of index. Per-build detail files live in the harvest tree._
