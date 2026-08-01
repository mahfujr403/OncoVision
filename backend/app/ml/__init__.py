"""AI Model Infrastructure package.

Contains model registry, manifest, cache, and download infrastructure.
This package must remain completely independent from API routers; routers
only consume services built on top of this package via dependency
injection. No TensorFlow, prediction, or ensemble logic exists here yet.
"""
