# Harvest Index — 2026-11-27 23:13:50 

## TL;DR

- **State:** ❗0 failed · 🔍0 suspicious · ⚠0 warnings · ✅10 clean · 🚫0 not-built
- **Action needed:** none — no actionable cross-build warnings
- **Since last run (`2026-11-27T22-25-42`):** ✅0 resolved · 🆕0 new · 🔀0 status changes

## 📊 Changes since 2026-11-27T22-25-42

### ✅ Resolved signatures (0)

_None._

### 🆕 New signatures (0)

_None._

### 🔀 Status changes (0)

_None._


## Overview

- **Diag root:** `/build/sources`
- **Harvest:**   `/build/harvest`
- **Branches:**  390xx
- **Builds:** 10 — ❗0 failed, 🔍0 suspicious, ⚠0 warn, ✅10 clean, 🚫0 not-built
- **Warning signatures:** 0 total — 0 actionable across multiple builds, 0 informational, 0 unique to one build
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
| 2 | 390xx | normal | 6.12.117-1-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 3 | 390xx | normal | 6.18.63-3-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 4 | 390xx | normal | 6.6.162-2-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 5 | 390xx | normal | 7.3.4-3-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 6 | 390xx | normal | 7.4.0-rc2-3-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 7 | 390xx | normal | 7.4.0-rc4-next-20261124-1-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 8 | 390xx | rt | 6.1.190-2-rt70-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 164942 |  |
| 9 | 390xx | rt | 6.12.116-1-rt22-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |
| 10 | 390xx | rt | 6.6.159-2-rt82-MANJARO | 390.157 | ✅ clean | 0 | 0 / 0 | 0 | 94474 |  |

## 🔁 Cross-build warning signatures

Warnings appearing in **more than one build**. Fixing the top signature fixes the most builds at once.

### 🎯 Actionable (driver source)

_None._

### ⚙️ Informational (build system / Makefile)

_None._

## 🧩 Unique to one build

Warnings in exactly **one** build. Usually kernel- or config-specific.

_No unique-to-one-build warnings._

---
_End of index. Per-build detail files live in the harvest tree._
