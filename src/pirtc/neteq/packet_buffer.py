from dataclasses import dataclass

from pirtc.neteq.packet import Packet, PacketPriority


@dataclass
class PacketBufferSmartFlushingConfig:
    # 如果采取smart flush，flush到的目标延迟，即保留的数据量
    target_level_threshold: int = 500
    # 出发smart flush的阈值，及超过target level的N倍后触发
    target_level_multiplier: int = 3


class PacketBuffer:
    def __init__(self,
                 max_number_of_packets,
                 tick_timer):
        self.max_number_of_packets = max_number_of_packets
        self.tick_timer = tick_timer
        self.buffer = []
        self.smart_flush_config = PacketBufferSmartFlushingConfig()
        self.count_dtx_waiting_time = False

    def flush(self):
        for p in self.buffer:
            # TODO: log discard packets
            pass
        self.buffer.clear()
        # TODO: log flush

    def partial_flush(self,
                      target_level_ms,
                      sample_rate,
                      last_decoded_length):
        # flush之后保留的数据量，至少是packet buffer最大数据的一半
        # 避免flush all导致卡顿过大
        target_level_samples = min(target_level_ms * sample_rate / 1000,
                                   self.max_number_of_packets * last_decoded_length / 2)
        # 避免flush得太低
        target_level_samples = max(target_level_samples,
                                   self.smart_flush_config.target_level_threshold * sample_rate / 1000)
        while self.get_span_samples(last_decoded_length, sample_rate, True) > target_level_samples or \
            len(self.buffer) > self.max_number_of_packets / 2:
            # TODO: log discard
            self.buffer.pop(0)

    def empty(self):
        return len(self.buffer) > 0

    def insert_packet(self,
                      packet: Packet,
                      last_decoded_length,
                      sample_rate,
                      target_level_ms,
                      decoder):
        pass

    def next_timestamp(self):
        if self.empty():
            return 'BUFFER_EMPTY'
        return self.buffer[0].timestamp

    def next_higher_timestamp(self, timestamp):
        pass

    def peak_next_packet(self):
        return None if self.empty() else self.buffer[0]

    def get_next_packet(self):
        if self.empty():
            return None

        packet = self.buffer[0]
        self.buffer.pop(0)
        return packet

    def discard_next_packet(self):
        if self.empty():
            return
        # TODO: log discard packet
        self.buffer.pop(0)

    def discard_old_packets(self,
                            timestamp_limit,
                            horizon_samples):
        pass

    def discard_all_old_packets(self,
                                timestamp_limit):
        pass

    def discard_packet_with_payload_type(self, payload_type):
        pass

    def num_packets_in_buffer(self):
        return len(self.buffer)

    def num_samples_in_buffer(self):
        num_samples = 0
        last_duration = 0
        for p in self.buffer:
            if p.frame:
                if p.priority != PacketPriority(0, 0):
                    continue
                duration = p.frame.duration()
                if duration > 0:
                    last_duration = duration
                num_samples += last_duration

        return num_samples

    def get_span_samples(self,
                         last_decoded_length,
                         sample_rate,
                         count_dtx_waiting_time):
        if len(self.buffer) == 0:
            return 0
        span = self.buffer[-1].timestamp - self.buffer[0].timestamp
        if self.buffer[-1].frame and self.buffer[-1].frame.duration() > 0:
            duration = self.buffer[-1].frame.duration()
            if self.count_dtx_waiting_time and self.buffer[-1].frame.is_dtx_packet():
                waiting_time_samples = self.buffer[-1].waiting_time.elapse_ms() * sample_rate / 1000
            span += duration
        return span

    def contain_dtx_or_cng_packets(self):
        # Opus是根据码流的标志，有些编码可能使用带外DTX方式
        for p in self.buffer:
            if p.frame and p.frame.is_dtx_packet():
                return True
        return False

    def is_obsolete_timestamp(self,
                              timestamp,
                              timestamp_limit,
                              horizon_samples):
        pass

