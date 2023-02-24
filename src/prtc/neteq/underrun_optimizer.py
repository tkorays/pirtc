from prtc.base.tick_timer import TickTimer, StopWatch
from prtc.neteq.histogram import Histogram

DELAY_BUCKETS = 100
BUCKET_SIZE_MS = 20


class UnderRunOptimizer:
    def __init__(self,
                 tick_timer: TickTimer,
                 hist_quantile: int,
                 forget_factor: int,
                 start_forget_weight: float = None,
                 resample_interval_ms: int = None):
        self.tick_timer = tick_timer
        self.hist_quantile = hist_quantile
        self.resample_interval_ms = resample_interval_ms
        self.hist = Histogram(DELAY_BUCKETS, forget_factor, start_forget_weight)
        self.resample_stopwatch = None
        self.max_delay_in_interval_ms = 0
        self.optimal_delay_ms = 0

    def update(self, relative_delay_ms: int):
        hist_update = relative_delay_ms
        if self.resample_interval_ms:
            if not self.resample_stopwatch:
                self.resample_stopwatch = StopWatch(self.tick_timer)

            if self.resample_stopwatch.elapsed_ms() > self.resample_interval_ms:
                hist_update = self.max_delay_in_interval_ms
                self.resample_stopwatch = StopWatch(self.tick_timer)
                self.max_delay_in_interval_ms = 0
            self.max_delay_in_interval_ms = max(self.max_delay_in_interval_ms, relative_delay_ms)

        if not hist_update:
            return

        index = hist_update / BUCKET_SIZE_MS
        if index < self.hist.num_buckets:
            self.hist.add(index)

        bucket_index = self.hist.quantile(self.hist_quantile)
        self.optimal_delay_ms = (1 + bucket_index) * BUCKET_SIZE_MS
        return self.optimal_delay_ms

    def get_optimal_delay_ms(self):
        return self.optimal_delay_ms

    def reset(self):
        self.hist.reset()
        self.resample_stopwatch = None
        self.max_delay_in_interval_ms = 0

