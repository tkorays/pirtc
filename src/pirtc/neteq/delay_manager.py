from dataclasses import dataclass
from copy import deepcopy

from pirtc.base.tick_timer import TickTimer
from pirtc.neteq.underrun_optimizer import UnderRunOptimizer
from pirtc.neteq.reorder_optimizer import ReorderOptimizer


START_DELAY_MS = 80
MAX_BASE_MINIMUM_DELAY_MS = 10000


@dataclass
class DelayManagerConfig:
    quantile: float = 0.95
    forget_factor: float = 0.983
    start_forget_weight: float = 2
    resample_interval_ms: int = 500

    use_reorder_optimizer: bool = True
    reorder_forget_factor: float = 0.9993
    ms_per_loss_percent: int = 20

    max_packets_in_buffer: int = 20
    base_minimum_delay_ms: int = 0


class DelayManager:
    def __init__(self,
                 config: DelayManagerConfig,
                 tick_timer: TickTimer):
        self.config = deepcopy(config)
        # 外部可以动态调整的最小延迟
        self.base_minimum_delay_ms = config.base_minimum_delay_ms
        # 实际生效的最小延迟
        self.effective_minimum_delay_ms = config.base_minimum_delay_ms
        # 设置的最大最小延迟
        self.minimum_delay_ms = 0
        self.maximum_delay_ms = 0
        self.packet_len_ms = 0
        self.target_level_ms = START_DELAY_MS
        self.unlimited_target_delay_ms = 0

        self.max_packets_in_buffer = config.max_packets_in_buffer
        self.underrun_optimizer = UnderRunOptimizer(tick_timer,
                                                    int((1 << 30) * config.quantile),
                                                    int((1 << 15) * config.forget_factor),
                                                    config.start_forget_weight,
                                                    config.resample_interval_ms)
        self.reorder_optimizer = ReorderOptimizer(int((1 << 15) * config.reorder_forget_factor),
                                                  config.ms_per_loss_percent,
                                                  config.start_forget_weight) if config.use_reorder_optimizer else None

    def update(self,
               arrival_delay_ms: int,
               reordered: bool):
        # 没有开启乱序或者非乱序，就走underrun，underrun不使用乱序包估计
        if not self.reorder_optimizer or not reordered:
            self.underrun_optimizer.update(arrival_delay_ms)
        self.target_level_ms = self.underrun_optimizer.get_optimal_delay_ms() or START_DELAY_MS

        if self.reorder_optimizer:
            self.reorder_optimizer.update(arrival_delay_ms, reordered, self.target_level_ms)
            self.target_level_ms = max(self.target_level_ms, self.reorder_optimizer.get_optimal_delay_ms())

        self.unlimited_target_delay_ms = self.target_level_ms
        self.target_level_ms = max(self.target_level_ms, self.effective_minimum_delay_ms)
        if self.maximum_delay_ms > 0:
            self.target_level_ms = min(self.target_level_ms, self.maximum_delay_ms)

        if self.packet_len_ms > 0:
            # 延迟只能到最大缓存数据的75%，避免溢出
            self.target_level_ms = min(self.target_level_ms, 3 * self.max_packets_in_buffer * self.packet_len_ms / 4)

    def reset(self):
        self.packet_len_ms = 0
        self.underrun_optimizer.reset()
        self.target_level_ms = START_DELAY_MS
        if self.reorder_optimizer:
            self.reorder_optimizer.reset()

    def get_target_delay_ms(self):
        return self.target_level_ms

    def get_unlimited_target_delay_ms(self):
        return self.unlimited_target_delay_ms

    def set_packet_audio_length(self, len_ms: int):
        if len_ms < 0:
            raise Exception("bad packet length")
        self.packet_len_ms = len_ms

    def set_minimum_delay(self, delay_ms):
        if not self.is_valid_base_minimum_delay(delay_ms):
            return False

        self.minimum_delay_ms = delay_ms
        self.update_effective_minimum_delay()
        return True

    def set_maximum_delay(self, delay_ms):
        if delay_ms != 0 and delay_ms < self.minimum_delay_ms:
            return False
        self.maximum_delay_ms = delay_ms
        self.update_effective_minimum_delay()
        return True

    def set_base_minimum_delay(self, delay_ms):
        if not self.is_valid_base_minimum_delay(delay_ms):
            return False

        self.base_minimum_delay_ms = delay_ms
        self.update_effective_minimum_delay()
        return True

    def get_base_minimum_delay(self):
        return self.base_minimum_delay_ms

    def update_effective_minimum_delay(self):
        # 实际生效的min_delay: max of minimum and base_minimum(这个是a音画同步动态调整的)
        base_minimum_delay_ms = 0 if self.base_minimum_delay_ms < 0 else self.base_minimum_delay_ms
        base_minimum_delay_ms = base_minimum_delay_ms if base_minimum_delay_ms < self.minimum_delay_upper_bound() \
            else self.minimum_delay_upper_bound()
        self.effective_minimum_delay_ms = max(self.minimum_delay_ms, base_minimum_delay_ms)

    def minimum_delay_upper_bound(self) -> int:
        # < quantile 75 of packet buffer
        # < 10s
        q75 = self.max_packets_in_buffer * self.packet_len_ms * 3 / 4
        q75 = q75 if q75 > 0 else MAX_BASE_MINIMUM_DELAY_MS
        maximum_delay_ms = self.maximum_delay_ms if self.maximum_delay_ms > 0 else MAX_BASE_MINIMUM_DELAY_MS
        return min(maximum_delay_ms, q75)

    @staticmethod
    def is_valid_base_minimum_delay(delay_ms):
        return 0 < delay_ms <= MAX_BASE_MINIMUM_DELAY_MS
