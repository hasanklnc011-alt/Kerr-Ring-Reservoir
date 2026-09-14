"""Local NARMA-10 benchmark package.

The canonical implementation is :mod:`benchmarks.narma10_np`. It generates
content-hashed deterministic trials and fail-closes blind evaluation until an
Astra-created candidate lock is present. It never invokes Tidy3D or the cloud.
"""

from __future__ import annotations

__all__ = [
    "narma10_np",
]

__version__ = "0.1.0"
