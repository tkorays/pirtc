

class TickTimer:
    def __init__(self, ms_per_tick: int = 10):
        self.ms_per_tick = ms_per_tick
        self.ticks = 0

    def increment(self, cnt: int = 1):
        self.ticks += cnt

    def get_ticks(self):
        return self.ticks

    def get_ms_per_tick(self):
        return self.ms_per_tick


class StopWatch:
    def __init__(self, tick_timer: TickTimer):
        self.tick_timer = tick_timer
        self.start_tick = tick_timer.get_ticks()

    def elapsed_ticks(self):
        return self.tick_timer.get_ticks() - self.start_tick

    def elapsed_ms(self):
        return self.elapsed_ticks() * self.tick_timer.get_ms_per_tick()


class CountDown:
    def __init__(self, tick_timer: TickTimer, ticks_to_count: int):
        self.tick_timer = tick_timer
        self.stop_watch = StopWatch(tick_timer)
        self.ticks_to_count = ticks_to_count

    def finished(self):
        return self.stop_watch.elapsed_ticks() >= self.ticks_to_count


if __name__ == "__main__":
    tt = TickTimer(10)
    tt.increment(5)
    print(tt.get_ticks())
    sw = StopWatch(tt)
    print(sw.elapsed_ms())
    tt.increment(5)
    print(sw.elapsed_ms())
    cd = CountDown(tt, 50)
    print(cd.finished())
    tt.increment(25)
    print(cd.finished())
    tt.increment(25)
    print(cd.finished())
