"""Prediction Engine package (ADR-008).

Produces individual, per-model predictions from every currently loaded AI
model for a single uploaded image. This package is intentionally isolated
from ensemble logic — ensemble voting is the responsibility of the
Adaptive Ensemble Engine (a future phase) and has no representation here.
"""
