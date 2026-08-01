"""Centralized Image Preprocessing pipeline (ADR-018, Phase 4.6.1).

Prepares validated uploaded images for AI inference: RGB conversion,
resizing, normalization, and batch tensor construction. Preprocessing
settings are sourced from the Model Manifest via `ModelRegistry` whenever
available, and fall back to a centralized default configuration
otherwise -- never hardcoded per model.

This package performs no AI inference. It never communicates with the AI
Runtime Manager, the Prediction Engine, or the Adaptive Ensemble Engine.
"""
