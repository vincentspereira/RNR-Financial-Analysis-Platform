"""
On-disk model registry for the analytics ML services.

Trained models together with their scaler and performance metadata are
persisted under ``MODEL_CACHE_DIR`` so they survive process restarts instead
of being retrained on every ``predict_*`` call. A staleness TTL
(``MODEL_CACHE_TTL_SECONDS``) controls how long a cached model is reused
before it is retrained.

All I/O is best-effort: registry failures NEVER break the train/predict path
-- if a read or write fails the caller simply retrains, exactly as before.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("model_registry")

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - joblib ships with scikit-learn
    JOBLIB_AVAILABLE = False


class ModelRegistry:
    """Filesystem-backed cache of (model, scaler, performance) bundles."""

    def __init__(
        self,
        base_dir: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        self.base_dir = Path(base_dir or getattr(settings, "MODEL_CACHE_DIR", "data/models"))
        self.ttl_seconds = (
            ttl_seconds
            if ttl_seconds is not None
            else float(getattr(settings, "MODEL_CACHE_TTL_SECONDS", 86400))
        )

    def _path_for(self, model_key: str) -> Path:
        # Keep the cache namespace-qualified and filesystem-safe.
        safe = model_key.replace("/", "_").replace(":", "_").replace(" ", "_")
        return self.base_dir / f"{safe}.joblib"

    @staticmethod
    def is_available() -> bool:
        """True when joblib is importable (it ships with scikit-learn)."""
        return JOBLIB_AVAILABLE

    def get(self, model_key: str) -> Optional[Tuple[Any, Any, Any]]:
        """Return ``(model, scaler, performance)`` for a fresh bundle, else ``None``."""
        if not JOBLIB_AVAILABLE:
            return None
        path = self._path_for(model_key)
        try:
            if not path.exists():
                return None
            if self._is_stale(path):
                logger.info(
                    "Cached model %s is stale (>%ss); will retrain",
                    model_key, self.ttl_seconds,
                )
                return None
            bundle = joblib.load(path)
            logger.info("Loaded cached model %s from %s", model_key, path)
            return bundle.get("model"), bundle.get("scaler"), bundle.get("performance")
        except Exception as e:  # never break predict on a cache-read failure
            logger.warning("Failed to load cached model %s: %s", model_key, e)
            return None

    def save(self, model_key: str, model: Any, scaler: Any, performance: Any) -> None:
        """Persist a trained bundle. Best-effort; failures are logged, not raised."""
        if not JOBLIB_AVAILABLE:
            return
        path = self._path_for(model_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".joblib.tmp")
            joblib.dump(
                {
                    "model": model,
                    "scaler": scaler,
                    "performance": performance,
                    "saved_at": time.time(),
                },
                tmp,
                compress=3,
            )
            os.replace(tmp, path)  # atomic on POSIX
            logger.info("Saved model %s to %s", model_key, path)
        except Exception as e:  # pragma: no cover - cache write must never break training
            logger.warning("Failed to save model %s: %s", model_key, e)

    def _is_stale(self, path: Path) -> bool:
        if self.ttl_seconds <= 0:
            return False  # <=0 means never expire
        age = time.time() - path.stat().st_mtime
        return age > self.ttl_seconds


# Shared singleton used by the analytics services.
model_registry = ModelRegistry()
