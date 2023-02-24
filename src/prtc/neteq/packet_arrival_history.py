from dataclasses import dataclass

from prtc.base.number_unwrapper import NumberUnwrapper


@dataclass
class PacketArrival:
    rtp_timestamp_ms: int = 0
    arrival_time_ms: int = 0

    def __le__(self, other):
        return self.arrival_time_ms - self.rtp_timestamp_ms <= other.arrival_time_ms - other.rtp_timestamp_ms

    def __ge__(self, other):
        return self.arrival_time_ms - self.rtp_timestamp_ms >= other.arrival_time_ms - other.rtp_timestamp_ms

    def __eq__(self, other):
        return self.rtp_timestamp_ms ==  other.rtp_timestamp_ms and self.arrival_time_ms == self.arrival_time_ms

    def str(self):
        return f'{self.rtp_timestamp_ms}_{self.arrival_time_ms}'

class PacketArrivalHistory:
    def __init__(self, window_size_ms: int):
        self.history = []
        self.min_packet_arrival = None
        self.max_packet_arrival = None
        self.sample_rate_hz = 0
        self.window_size_ms = window_size_ms
        self.newest_rtp_timestamp = None
        self.timestamp_unwrapper = NumberUnwrapper(32)

    def insert(self, rtp_timestamp: int, arrival_time_ms: int):
        unwrapped_rtp_timestamp = self.timestamp_unwrapper.unwrap(rtp_timestamp)
        if not self.newest_rtp_timestamp:
            self.newest_rtp_timestamp = unwrapped_rtp_timestamp
        if unwrapped_rtp_timestamp > self.newest_rtp_timestamp:
            self.newest_rtp_timestamp = unwrapped_rtp_timestamp

        self.history.append(PacketArrival(unwrapped_rtp_timestamp / self.sample_rate_hz, arrival_time_ms))
        self.maybe_update_cached_arrivals(self.history[-1])

        while len(self.history) > 0:
            if self.history[0].rtp_timestamp_ms + self.window_size_ms < unwrapped_rtp_timestamp / self.sample_rate_hz:
                if self.history[0] == self.min_packet_arrival:
                    self.min_packet_arrival = None
                if self.history[0] == self.max_packet_arrival:
                    self.max_packet_arrival = None
                self.history.pop(0)
            else:
                break
        if not self.min_packet_arrival or not self.max_packet_arrival:
            for p in self.history:
                self.maybe_update_cached_arrivals(p)

    def maybe_update_cached_arrivals(self, p: PacketArrival):
        if not self.min_packet_arrival or p <= self.min_packet_arrival:
            self.min_packet_arrival = p
        if not self.max_packet_arrival or p >= self.max_packet_arrival:
            self.max_packet_arrival = p

    def get_delay_ms(self, rtp_timestamp: int, time_ms: int) -> int:
        unwrapped_rtp_timestamp_ms = self.timestamp_unwrapper.peek_unwrap(rtp_timestamp) / self.sample_rate_hz
        return self.get_packet_arrival_delay_ms(PacketArrival(unwrapped_rtp_timestamp_ms, time_ms))

    def get_max_delay_ms(self):
        if not self.max_packet_arrival:
            return 0
        return self.get_packet_arrival_delay_ms(self.max_packet_arrival)

    def is_newest_rtp_timestamp(self, rtp_timestamp: int):
        if not self.newest_rtp_timestamp:
            return False
        return self.timestamp_unwrapper.peek_unwrap(rtp_timestamp) == self.newest_rtp_timestamp

    def reset(self):
        self.history.clear()
        self.min_packet_arrival = None
        self.max_packet_arrival = None
        self.timestamp_unwrapper = NumberUnwrapper(32)
        self.newest_rtp_timestamp = None

    def set_sample_rate(self, sample_rate: int):
        self.sample_rate_hz = sample_rate

    def size(self):
        return len(self.history)

    def get_packet_arrival_delay_ms(self, p: PacketArrival):
        if not self.min_packet_arrival:
            return 0
        return max(p.arrival_time_ms - self.min_packet_arrival.arrival_time_ms\
                   - (p.rtp_timestamp_ms - self.min_packet_arrival.rtp_timestamp_ms), 0)
