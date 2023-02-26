
class NumberUnwrapper:
    def __init__(self, bits: int):
        self.last_unwrapped = 0
        self.last_value = None
        self.wrap = 0
        if bits == 8:
            self.wrap = 0x0ff
        elif bits == 16:
            self.wrap = 0x00ffff
        elif bits == 32:
            self.wrap = 0x00ffffffff
        if self.wrap == 0:
            raise Exception(f"not support for {bits}bits")

    def unwrap(self, num):
        if not self.last_value:
            self.last_value = num
        else:
            wrap = self.wrap + 1
            self.last_unwrapped += (num - self.last_value if self.last_value < num else wrap - (self.last_value - num))
            if num > self.last_value and num - self.last_value > wrap / 2:
                self.last_unwrapped -= wrap

        self.last_value = num
        return self.last_unwrapped

    def peek_unwrap(self, num):
        if not self.last_value:
            return None
        wrap = self.wrap + 1
        last_unwrapped = self.last_unwrapped + (num - self.last_value if self.last_value < num else wrap - (self.last_value - num))
        if num > self.last_value and num - self.last_value > wrap / 2:
            last_unwrapped -= wrap
        return last_unwrapped
