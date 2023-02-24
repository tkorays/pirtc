

class PacketPriority:
    def __init__(self):
        # 包类型
        # 媒体包：<0, 0>
        # FEC包：<1, 0>
        # inband FEC: <2, 0>
        # 媒体包重传：<0, 1>
        # FEC包重传：<1, 1>
        self.codec_level = 0
        self.red_level = 0

    def __lt__(self, other):
        return self.red_level < other.red_level if self.codec_level == other.codec_level \
            else self.codec_level < other.codec_level

    def __gt__(self, other):
        return self.red_level > other.red_level if self.codec_level == other.codec_level \
            else self.codec_level > other.codec_level

    def __eq__(self, other):
        return self.codec_level == other.codec_level and self.red_level == other.red_level

    def __le__(self, other):
        return not self.__gt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)


class Packet:
    def __init__(self):
        self.timestamp = 0
        self.sequence_number = 0
        self.payload_type = 0
        self.payload = PacketPriority()
        self.priority = 0


