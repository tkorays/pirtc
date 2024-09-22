import math


class LinkCapacityEstimator:
    """
    这里的前提是：假设链路带宽满足正态分布。
    因此，用平均值+3倍标准差作为上界，用平均值-3倍标准差作为下界。
    3 sigma覆盖了99.7%的情况，在剔除了极少数异常值情况下，能够覆盖整体情况。
    """
    def __init__(self):
        # 估计的码率（滑动平均码率）
        self.estimate_bitrate_bps: int = 0
        # 估计码率方差（归一化的），表示1个单位码率下，方差是平均码率的几倍，因此单位是bps
        self.bitrate_deviation_bps: float = 0.4

    def upper_bound(self) -> int:
        if self.estimate_bitrate_bps > 0:
            return int(self.estimate_bitrate_bps + 3 * self.bitrate_deviation_bps)
        return 0

    def lower_bound(self) -> int:
        if self.estimate_bitrate_bps > 0:
            return max(0, int(
                self.estimate_bitrate_bps - 3 * self.bitrate_deviation_bps
            ))
        return 0

    def reset(self) -> None:
        self.estimate_bitrate_bps = 0

    def on_overuse_detected(self, ack_bitrate_bps: int) -> None:
        # overuse得到的带宽置信度非常不高
        self._update(ack_bitrate_bps, 0.05)

    def on_probe_bitrate(self, probe_bitrate_bps) -> None:
        self._update(probe_bitrate_bps, 0.5)

    def has_estimate(self) -> bool:
        return self.estimate_bitrate_bps > 0

    def estimate_bps(self) -> int:
        return self.estimate_bitrate_bps

    def std_deviation_bps(self) -> int:
        return int(math.sqrt(self.bitrate_deviation_bps * self.estimate_bitrate_bps))

    def _update(self, bitrate_bps, alpha):
        # 输入最新的码率，以及更新参数，更新平均值和标准差
        if self.estimate_bitrate_bps <= 0:
            self.estimate_bitrate_bps = bitrate_bps
        else:
            self.estimate_bitrate_bps = (1 - alpha) * self.estimate_bitrate_bps + alpha * bitrate_bps

        norm = max(self.estimate_bitrate_bps, 1)
        error_bps = self.estimate_bitrate_bps - bitrate_bps
        self.bitrate_deviation_bps = (1 - alpha) * self.bitrate_deviation_bps + alpha * error_bps * error_bps / norm

        self.bitrate_deviation_bps = max(self.bitrate_deviation_bps, 0.4)
        self.bitrate_deviation_bps = min(self.bitrate_deviation_bps, 2.5)