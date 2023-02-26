
AUDIO_SPEECH_TYPE_SPEECH = 1
AUDIO_SPEECH_TYPE_COMFORT_NOISE = 2


class EncodedAudioFrame:
    def __init__(self):
        pass

    def duration(self) -> int:
        pass

    def is_dtx_packet(self) -> bool:
        pass

    def decode(self, b):
        pass
