"""
Powered by tkorays. All rights reserved.
"""

class Histogram:
    def __init__(self, num_buckets, forget_factor, start_forget_weight):
        self.num_buckets = num_buckets
        self.forget_factor = 0
        self.base_forget_factor = forget_factor
        self.start_forget_weight = start_forget_weight
        self.buckets = [0 for i in range(self.num_buckets)]
        self.add_cnt = 0

    def reset(self):
        tmp_prob = 0x4002
        for i in range(self.num_buckets):
            tmp_prob = tmp_prob >> 1
            self.buckets[i] = tmp_prob << 16
        self.forget_factor = 0
        self.add_cnt = 0

    def add(self, index):
        vector_sum = 0
        # 老的数据全部乘上一个遗忘系数，Q30*Q15 >> 15
        for i in range(self.num_buckets):
            self.buckets[i] = int(self.buckets[i] * self.forget_factor) >> 15
            vector_sum += self.buckets[i]

        # 新的数据 x (1 - 遗忘系数)，Q15 << 15
        self.buckets[index] += (32768 - self.forget_factor) << 15
        vector_sum += (32768 - self.forget_factor) << 15

        # bucket中所有数据的和应该为1，运算会存在一点偏差(1~2)，将偏差分配到有数据的bucket上面
        vector_sum -= 1 << 30
        if vector_sum != 0:
            flip_sign = -1 if vector_sum > 0 else 1
            for i in range(self.num_buckets):
                correction = flip_sign * min(abs(vector_sum), self.buckets[i])
                self.buckets[i] += correction
                vector_sum += correction
                if abs(vector_sum) == 0:
                    break

        self.add_cnt += 1
        if self.start_forget_weight >= 0:
            if self.forget_factor != self.base_forget_factor:
                forget_factor = int((1 << 15) * (1 - self.start_forget_weight / (self.add_cnt + 1)))
                self.forget_factor = max(0, min(self.base_forget_factor, forget_factor))
        else:
            # 这里最终会收敛到设置的factor
            self.forget_factor += (self.base_forget_factor - self.forget_factor + 3) >> 2

    def quantile(self, probability) -> int:
        inverse_probability = (1 << 30) - probability
        index = 0
        bucket_sum = 1 << 30
        bucket_sum -= self.buckets[index]
        while bucket_sum > inverse_probability and index < self.num_buckets:
            index += 1
            bucket_sum -= self.buckets[index]
        return index

