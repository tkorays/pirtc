import matplotlib.pyplot as plt
from pirtc.neteq.histogram import Histogram


def simulate(forget_factor, start_weight):
    result = []
    factor = []
    QUANTILE = int((1 << 30) * 0.95)

    hist = Histogram(100, forget_factor, start_weight)
    hist.reset()

    hist.add(20)
    result.append(hist.quantile(QUANTILE))
    factor.append(hist.forget_factor / 32768)

    hist.add(20)
    result.append(hist.quantile(QUANTILE))
    factor.append(hist.forget_factor / 32768)

    hist.add(1)
    result.append(hist.quantile(QUANTILE))
    factor.append(hist.forget_factor / 32768)

    for i in range(300):
        hist.add(0)
        result.append(hist.quantile(QUANTILE))
        factor.append(hist.forget_factor / 32768)

    return result, factor


def main():
    factor = int((1 << 15) * 0.999)

    fig, axs = plt.subplots(2, 1)
    for i in range(3):
        ri, fi = simulate(factor, [-1, 1, 2][i])
        axs[0].plot(fi, ['--', 'r', 'b'][i], label=['old', 'new', 'new1'][i])
        axs[1].plot(ri, ['--', 'r', 'b'][i], label=['old', 'new', 'new1'][i])

    axs[0].title.set_text("forget factor")
    axs[0].legend()
    axs[1].title.set_text('target delay')
    axs[1].legend()
    plt.show()


if __name__ == '__main__':
    main()
