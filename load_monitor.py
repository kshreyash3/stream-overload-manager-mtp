"""
Load Monitor + Smart Valve
Watches queue depth and decides which processing mode to use.
"""

import queue
import threading
import time


class LoadMonitor:
    """
    Continuously samples the queue size and computes a smoothed load score.
    Fires mode-change callbacks when thresholds are crossed.
    """
    def __init__(self, q: queue.Queue,
                 high_threshold: int = 500,
                 low_threshold: int = 200,
                 sample_interval: float = 0.1):
        self.q               = q
        self.high_threshold  = high_threshold
        self.low_threshold   = low_threshold
        self.sample_interval = sample_interval

        self.current_load    = 0
        self._overloaded     = False
        self._running        = False
        self._callbacks      = []   # called with (True/False) on mode change
        self._lock           = threading.Lock()

    # ── public API ────────────────────────────────────────────────────────
    def is_overloaded(self) -> bool:
        with self._lock:
            return self._overloaded

    def on_mode_change(self, fn):
        """Register a callback: fn(overloaded: bool)"""
        self._callbacks.append(fn)

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    # ── internal ──────────────────────────────────────────────────────────
    def _loop(self):
        while self._running:
            size = self.q.qsize()
            with self._lock:
                self.current_load = size
                was_overloaded = self._overloaded

                if not self._overloaded and size >= self.high_threshold:
                    self._overloaded = True
                elif self._overloaded and size <= self.low_threshold:
                    self._overloaded = False

                if self._overloaded != was_overloaded:
                    for fn in self._callbacks:
                        fn(self._overloaded)

            time.sleep(self.sample_interval)


class SmartValve:
    """
    Routes incoming events to Normal or Adaptive mode based on LoadMonitor.
    """
    NORMAL   = "NORMAL"
    ADAPTIVE = "ADAPTIVE"

    def __init__(self, monitor: LoadMonitor):
        self.monitor = monitor
        self.mode    = self.NORMAL
        monitor.on_mode_change(self._on_mode_change)

    def _on_mode_change(self, overloaded: bool):
        self.mode = self.ADAPTIVE if overloaded else self.NORMAL
        print(f"\n[SmartValve] ⚡ Mode → {self.mode}")

    def current_mode(self) -> str:
        return self.ADAPTIVE if self.monitor.is_overloaded() else self.NORMAL
