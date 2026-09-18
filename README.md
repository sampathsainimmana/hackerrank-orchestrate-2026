# HackerRank Orchestrate 2026 — Buy or Wait?

A deterministic financial decision engine developed for HackerRank Orchestrate 2026.

## Overview

The project evaluates purchase requests using a forward-looking cash-flow model. It accounts for minimum balance requirements, dated financial events, confirmed income, exchange rates, recurring commitments, payment options, and image-backed transaction amounts.

## Core approach

- Deterministic decision logic
- Decimal-based financial calculations
- Fixed exchange-rate lookup
- Conservative handling of unresolved financial events
- 90-day cash-flow simulation
- Validation of supplied payment schedules
- Support for full payment, partial payment, installments, waiting, and spending adjustments

The runtime engine does not require an LLM, keeping decisions reproducible and auditable.

## Technology

- Python 3.10+
- Python standard library
- No third-party runtime dependencies

## Main file

- `engine.py` — financial data loading, event processing, cash-flow simulation, payment-plan validation, and request evaluation.

## Note

This repository contains the cleaned participant-side implementation. Challenge-internal agent instructions, session logs, and development transcripts are intentionally excluded.
