"""
Temporal Filtering & Smoothing
Implements Exponential Moving Average (EMA) to suppress high-frequency landmark jitter.
"""

from typing import Dict, Optional
import numpy as np


class ExponentialMovingAverageFilter:
    """
    Online Exponential Moving Average (EMA) smoother for real-time streaming data.
    Formula:
        S_t = alpha * Y_t + (1 - alpha) * S_{t-1}
    where alpha in (0.0, 1.0] controls responsiveness vs. smoothing strength.
    """

    def __init__(self, alpha: float = 0.65):
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be in (0.0, 1.0]")
        self.alpha = alpha
        self._state: Dict[str, np.ndarray] = {}

    def filter_point(self, key: str, value: np.ndarray) -> np.ndarray:
        """
        Applies EMA smoothing to an array/point.
        """
        val_arr = np.array(value, dtype=np.float64)
        if key not in self._state:
            self._state[key] = val_arr
            return val_arr

        smoothed = self.alpha * val_arr + (1.0 - self.alpha) * self._state[key]
        self._state[key] = smoothed
        return smoothed

    def filter_scalar(self, key: str, value: Optional[float]) -> Optional[float]:
        """
        Applies EMA smoothing to a scalar value (e.g. joint angle).
        """
        if value is None:
            return None

        if key not in self._state:
            self._state[key] = np.array([value], dtype=np.float64)
            return value

        smoothed = self.alpha * float(value) + (1.0 - self.alpha) * float(self._state[key][0])
        self._state[key][0] = smoothed
        return round(float(smoothed), 2)

    def reset(self, key: Optional[str] = None) -> None:
        """
        Resets the filter memory for a key or all keys.
        """
        if key:
            self._state.pop(key, None)
        else:
            self._state.clear()
