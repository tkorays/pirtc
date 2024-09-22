import math
from idlelib.run import Executive

from .link_capacity_estimator import LinkCapacityEstimator


class AimdRateControl:
    RC_STATE_HOLD = 0
    RC_STATE_INC = 1
    RC_STATE_DEC = 2

    BW_USAGE_NORMAL = 0
    BW_USAGE_UNDERUSING = 1
    BW_USAGE_OVERUSING = 2
    BW_USAGE_LAST = 3

    """
    AIMD, Additive Increase Multiplication Decrease
    - 没有overuse的时候可以线性增加，overuse出现后，按照指数降低。
    - 但是在慢启动（slow start）阶段，我们也会做指数级增加。
    """
    def __init__(self):
        # 5k~30M
        self.min_conf_bitrate = 5000
        self.max_conf_bitrate = 30000000
        self.current_bitrate = self.max_conf_bitrate
        self.latest_est_throughput = self.current_bitrate
        self.link_capacity = LinkCapacityEstimator()
        self.rate_ctrl_state = AimdRateControl.RC_STATE_HOLD
        self.time_last_bitrate_change = 0
        self.time_last_bitrate_decrease = 0
        self.time_first_throughput_est = 0

        self.bitrate_is_initialized = False
        self.beta = 0.85
        self.in_alr = False
        self.rtt = 200
        self.send_side = True # delete!!!
        self.no_bitrate_increase_in_alr = True
        self.last_decrease = 0

    def valid_estimate(self) -> bool:
        return self.bitrate_is_initialized

    def set_start_bitrate(self, bitrate_bps) -> None:
        self.current_bitrate = bitrate_bps
        self.latest_est_throughput = bitrate_bps
        self.bitrate_is_initialized = True

    def set_min_bitrate(self, bitrate_bps) -> None:
        self.min_conf_bitrate = bitrate_bps
        self.current_bitrate = max(self.min_conf_bitrate, self.current_bitrate)

    def get_feedback_interval_ns(self) -> int:
        # 根据当前状态，决定是否需要降低RTCP的频率
        # TODO: fill this function
        pass

    def time_to_reduce_further(self, ts: int, estimate_throughput: int) -> bool:
        """
        用于确定overuse后是否需要降低带宽。
        """
        reduction_interval = min(max(10, self.rtt), 200)
        if ts - self.time_last_bitrate_change >= reduction_interval:
            # 超过一个rtt带宽没有变化
            return True

        if self.valid_estimate():
            # 吞吐率不足上次估计的一半
            threshold = 0.5 * self.latest_estimate()
            return estimate_throughput < threshold

        return False

    def initial_time_to_reduce_further(self, ts: int) -> bool:
        return self.valid_estimate() and self.time_to_reduce_further(
            # 一定是返回true?
            ts, int(self.latest_estimate() / 2 - 1)
        )

    def latest_estimate(self) -> int:
        return self.current_bitrate

    def set_rtt(self, rtt: int):
        self.rtt = rtt

    def update(self, state: int, bitrate: int, ts: int) -> int:
        if not self.bitrate_is_initialized:
            # 初始化，第一次的值不要使用，等到5s后才使用
            initialization_time_ms = 5000
            if self.time_first_throughput_est <= 0:
                # 还没有估计过，记录第一次有效的值
                if bitrate > 0:
                    self.time_first_throughput_est = ts
            elif ts - self.time_first_throughput_est > initialization_time_ms and bitrate > 0:
                # 初始化完成
                self.current_bitrate  = bitrate
                self.bitrate_is_initialized = True

        self._change_bitrate(state, bitrate, ts)
        return self.current_bitrate

    def set_in_alr(self, in_alr: bool) -> None:
        self.in_alr = in_alr

    def set_estimate(self, bitrate: int, ts: int):
        self.bitrate_is_initialized = True
        prev_bitrate = self.current_bitrate
        self.current_bitrate = self._clamp_bitrate(bitrate)
        self.time_last_bitrate_change = ts
        if self.current_bitrate < prev_bitrate:
            self.time_last_bitrate_decrease = ts

    def set_network_state_estimate(self, est: int):
        pass

    def get_near_max_increase_rate_bps_per_second(self) -> int:
        # 这里假设视频帧30fps
        frame_interval = 1000 / 30
        frame_size = self.current_bitrate * frame_interval
        # 假设每个帧1200字节
        packet_bytes = 1200
        packet_per_frame = math.ceil(frame_size / packet_bytes)
        avg_pkt_size = frame_size / packet_per_frame

        response_time = self.rtt + 100
        response_time = response_time * 2

        # bit / ms，每个响应时间（2*rtt）至少增加一个视频包的码率
        increase_bps_per_second = int(1000 * avg_pkt_size / response_time)
        return max(4000, increase_bps_per_second)

    def get_exp_bandwidth_period(self) -> int:
        # 2s, 3s, 50s
        min_period = 2000
        default_period = 3000
        max_period = 50000

        increase_bps_per_second = self.get_near_max_increase_rate_bps_per_second()
        if self.last_decrease <= 0:
            return default_period

        time_to_recover_decrease = int(self.last_decrease / increase_bps_per_second) * 1000
        return min(max(time_to_recover_decrease, min_period), max_period)


    def _change_bitrate(self, state: int, bitrate: int, ts: int):
        est_throughput = bitrate if bitrate > 0 else self.latest_est_throughput
        if bitrate > 0:
            self.latest_est_throughput = bitrate

        if not self.bitrate_is_initialized and state != AimdRateControl.BW_USAGE_OVERUSING:
            # 只要是非overuse状态，没有初始化就需要退出
            # 但是如果是overuse状态，还没有初始化状态，我们也需要去响应
            return

        # 状态机
        self._change_state(state, bitrate, ts)

        new_bitrate = 0

        # 码率调整
        if self.rate_ctrl_state == AimdRateControl.RC_STATE_HOLD:
            # hold状态，无需要做码率调整
            pass
        elif self.rate_ctrl_state == AimdRateControl.RC_STATE_INC:
            if est_throughput > self.link_capacity.upper_bound():
                # 当前的码率超过了link capacity的上限，可能是带宽瓶颈发生了变化
                # 比如网络受限取消了
                self.link_capacity.reset()

            # 限制了码率增加太多
            increase_limit = 1.5 * est_throughput + 10 * 1000

            if self.send_side and self.in_alr and self.no_bitrate_increase_in_alr:
                # ALR阶段，不去增加码率
                increase_limit = self.current_bitrate

            if self.current_bitrate < increase_limit:
                increased_bitrate = -1
                if self.link_capacity.has_estimate():
                    additive_increase = self._additive_rate_increase(ts, self.time_last_bitrate_change)
                    increased_bitrate = self.current_bitrate + additive_increase
                else:
                    # 慢启动阶段，link capacity没有结果，这个时候需要乘性增加
                    multiplicative_incrase = self._multiplicative_rate_increase(ts, self.time_last_bitrate_change, self.current_bitrate)
                    increased_bitrate = self.current_bitrate + multiplicative_incrase
                new_bitrate = min(increased_bitrate, increase_limit)

            self.time_last_bitrate_change = ts
        elif self.rate_ctrl_state == AimdRateControl.RC_STATE_DEC:
            decreased_bitrate = -1
            decreased_bitrate = est_throughput * self.beta

            # 这里设置码率稍低于估计的吞吐量，为了消除自引入的延时（感觉没必要）
            if decreased_bitrate > 5000:
                decreased_bitrate -= 5000

            if decreased_bitrate > self.current_bitrate:
                # 如果按照当前ack的码率计算，乘以0.85后，高于当前估计带宽，则使用link capacity的计算结果
                if self.link_capacity.has_estimate():
                    decreased_bitrate = self.link_capacity.estimate_bps() * self.beta

            new_bitrate = -1
            if decreased_bitrate < self.current_bitrate:
                new_bitrate = decreased_bitrate

            if self.bitrate_is_initialized and est_throughput < self.current_bitrate:
                if new_bitrate <= 0:
                    self.last_decrease = 0
                else:
                    self.last_decrease = self.current_bitrate - new_bitrate

            if est_throughput < self.link_capacity.lower_bound():
                # 当前吞吐率远低于link capacity结果，需要重置link capacity
                self.link_capacity.reset()

            self.bitrate_is_initialized = True
            self.link_capacity.on_overuse_detected(est_throughput)
            # 每次降低后，重新进入到hold状态
            self.rate_ctrl_state = AimdRateControl.RC_STATE_HOLD
            self.time_last_bitrate_change = ts
            self.time_last_bitrate_decrease = ts
        else:
            raise Exception("bad rate control state")

        self.current_bitrate = self._clamp_bitrate(new_bitrate if new_bitrate > 0 else self.current_bitrate)

    def _clamp_bitrate(self, bitrate: int) -> int:
        # TODO: disable estimate bounded increase
        # TODO: 使用net capacity结果限制

        new_bitrate = bitrate
        new_bitrate = max(new_bitrate, self.min_conf_bitrate)
        return bitrate

    def _multiplicative_rate_increase(self, ts: int, last_ts: int, current_bitrate):
        alpha = 1.08
        if last_ts  > 0:
            time_since_last_update = ts - last_ts
            alpha = math.pow(alpha, min(1.0, time_since_last_update / 1000))
        increase = max(current_bitrate * (alpha - 1.0), 1000)
        return increase

    def _additive_rate_increase(self, ts: int, last_ts):
        time_period_seconds = ts - last_ts
        increase = self.get_near_max_increase_rate_bps_per_second() * time_period_seconds
        return increase

    def _change_state(self, state: int, bitrate: int, ts: int):
        if state == AimdRateControl.BW_USAGE_NORMAL:
            # overuse -> normal, underuse->normal
            if self.rate_ctrl_state == AimdRateControl.RC_STATE_HOLD:
                self.time_last_bitrate_change = ts
                self.rate_ctrl_state = AimdRateControl.RC_STATE_INC
        elif state == AimdRateControl.BW_USAGE_OVERUSING:
            # 遇到overuse，一律降低带宽
            if self.rate_ctrl_state != AimdRateControl.RC_STATE_DEC:
                self.rate_ctrl_state = AimdRateControl.RC_STATE_DEC
        elif state == AimdRateControl.BW_USAGE_UNDERUSING:
            # under use不会触发任何动作，等到normal状态才会增加带宽
            self.rate_ctrl_state = AimdRateControl.RC_STATE_HOLD
        else:
            raise Exception("bad state")