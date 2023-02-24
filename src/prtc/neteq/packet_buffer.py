
class PacketBuffer:
    def __init__(self,
                 max_number_of_packets,
                 tick_timer):
        self.max_number_of_packets = max_number_of_packets
        self.tick_timer = tick_timer
        self.buffer = []

    def flush(self):
        pass

    def partial_flush(self):
        pass

    def empty(self):
        pass

    def insert_packet(self,
                      packet,
                      last_decoded_length,
                      sample_rate,
                      target_level_ms,
                      decoder):
        pass

    def next_timestamp(self):
        pass

    def next_higher_timestamp(self, timestamp):
        pass

    def peak_next_packet(self):
        pass

    def get_next_packet(self):
        pass

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
        pass

    def num_samples_in_buffer(self):
        pass

    def get_span_samples(self,
                         last_decoded_length,
                         sample_rate,
                         count_dtx_waiting_time):
        pass

    def contain_dtx_or_cng_packets(self):
        pass

    def is_obsolete_timestamp(self,
                              timestamp,
                              timestamp_limit,
                              horizon_samples):
        pass

