from prtc.neteq.histogram import Histogram

DELAY_BUCKETS = 100
BUCKET_SIZE_MS = 20


class ReorderOptimizer:
    """
    乱序估计
    """
    def __init__(self,
                 forget_factor: int,
                 ms_per_lost_percent: int,
                 start_forget_weight: float = None):
        self.hist = Histogram(DELAY_BUCKETS, forget_factor, start_forget_weight)
        self.ms_per_loss_percent = ms_per_lost_percent
        self.optimal_delay_ms = None

    def update(self,
               relative_delay_ms: int,
               reordered: bool,
               base_delay: int):
        index = relative_delay_ms / BUCKET_SIZE_MS if reordered else 0
        if index < self.hist.num_buckets:
            self.hist.add(index)

        bucket_index = self.minimize_cost_function(base_delay)
        self.optimal_delay_ms = (1 + bucket_index) * BUCKET_SIZE_MS

    def get_optimal_delay_ms(self):
        return self.optimal_delay_ms

    def reset(self):
        self.hist.reset()
        self.optimal_delay_ms = None

    def minimize_cost_function(self, base_delay_ms: int):
        loss_probability = 1 << 30  # 100%
        min_cost = 18446744073709551615  # max int64
        min_buckets = 0
        for i in range(self.hist.num_buckets):
            # 如果以i为最终结果，将导致多少的丢包，这里是jitter buffer主动丢弃
            loss_probability -= self.hist.buckets[i]
            # 如果以i为最终结果，将会多引入多长时间的延迟
            delay_ms = max(0, i * BUCKET_SIZE_MS - base_delay_ms) << 30
            # 每丢1%的包，需要增加ms_per_loss_percent延迟来抗
            # 总代价就是为了超过基础延迟的部分和为了抗剩余丢包的部分
            cost = delay_ms + 100 * self.ms_per_loss_percent * loss_probability
            # 迭代得到最低的带宽
            if cost < min_cost:
                min_cost = cost
                min_buckets = i

            if loss_probability == 0:
                break
        return min_buckets
