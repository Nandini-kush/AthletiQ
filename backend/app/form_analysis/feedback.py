"""
Feedback Stabilization & Temporal Debouncing
Maintains temporal confirmation windows, repeat-finding cooldowns, and stale finding clearing to prevent UI flooding.
"""

import time
from typing import Dict, List, Optional
from app.form_analysis.schemas import FormFinding


class FeedbackStabilizer:
    """
    Stabilizes real-time rule findings by enforcing:
    1. Confirmation dwell (must be observed over consecutive frames to avoid frame-jitter false alarms).
    2. Cooldown timer (prevents repeating the same finding too rapidly).
    3. Stale finding clearing.
    """

    def __init__(
        self,
        confirmation_frames: int = 2,
        cooldown_seconds: float = 1.8,
        stale_frames_to_clear: int = 3,
    ):
        self.confirmation_frames = confirmation_frames
        self.cooldown_seconds = cooldown_seconds
        self.stale_frames_to_clear = stale_frames_to_clear

        # code -> consecutive frame count
        self._consecutive_hits: Dict[str, int] = {}
        # code -> last emitted timestamp
        self._last_emitted_time: Dict[str, float] = {}
        # code -> FormFinding
        self._active_findings: Dict[str, FormFinding] = {}
        # code -> consecutive missed frames
        self._missed_hits: Dict[str, int] = {}

    def filter_findings(
        self,
        raw_findings: List[FormFinding],
        timestamp: Optional[float] = None,
    ) -> List[FormFinding]:
        """
        Processes candidate raw findings and returns stable, debounced findings.
        """
        now = timestamp if timestamp is not None else time.time()
        observed_codes = {f.code for f in raw_findings}

        # 1. Update hit counts for observed findings
        for finding in raw_findings:
            code = finding.code
            self._consecutive_hits[code] = self._consecutive_hits.get(code, 0) + 1
            self._missed_hits[code] = 0

            # Check if confirmed
            if self._consecutive_hits[code] >= self.confirmation_frames:
                last_time = self._last_emitted_time.get(code, 0.0)
                if (now - last_time) >= self.cooldown_seconds or code not in self._active_findings:
                    self._active_findings[code] = finding
                    self._last_emitted_time[code] = now

        # 2. Update missed counts for unobserved findings and clear stale ones
        for code in list(self._active_findings.keys()):
            if code not in observed_codes:
                self._missed_hits[code] = self._missed_hits.get(code, 0) + 1
                if self._missed_hits[code] >= self.stale_frames_to_clear:
                    self._active_findings.pop(code, None)
                    self._consecutive_hits.pop(code, None)

        for code in list(self._consecutive_hits.keys()):
            if code not in observed_codes:
                self._consecutive_hits[code] = 0

        return list(self._active_findings.values())

    def reset(self) -> None:
        """Clears all internal confirmation buffers, cooldowns, and active findings."""
        self._consecutive_hits.clear()
        self._last_emitted_time.clear()
        self._active_findings.clear()
        self._missed_hits.clear()
