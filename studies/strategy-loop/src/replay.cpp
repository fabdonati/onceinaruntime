#include "replay.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace strategy {
namespace {
std::size_t product(std::size_t a, std::size_t b) {
    if (b != 0 && a > std::numeric_limits<std::size_t>::max() / b)
        throw std::invalid_argument("dimension product overflows");
    return a * b;
}

template<bool Diagnose>
inline void step(State& state, bool target, const Bar& bar, bool last,
                 const Rules& rules, Trace* trace) {
    double opening_fee = 0.0;
    int event = 0;
    if (target && state.shares == 0.0) {
        state.shares = state.cash / (bar.open * (1.0 + rules.fee));
        const double notional = state.shares * bar.open;
        opening_fee = notional * rules.fee;
        state.cash = 0.0;
        state.notional += notional;
        state.fees += opening_fee;
        ++state.trades;
        event = 1;
    } else if (!target && state.shares != 0.0) {
        const double notional = state.shares * bar.open;
        opening_fee = notional * rules.fee;
        state.cash = notional * (1.0 - rules.fee);
        state.shares = 0.0;
        state.notional += notional;
        state.fees += opening_fee;
        ++state.trades;
        event = -1;
    }
    if constexpr (Diagnose) {
        trace->target_long = target;
        trace->opening_event = event;
        trace->cash_after_open = state.cash;
        trace->shares_after_open = state.shares;
        trace->opening_fee = opening_fee;
        trace->liquidation_fee = 0.0;
    }
    if (last && state.shares != 0.0) {
        const double notional = state.shares * bar.close;
        const double fee = notional * rules.fee;
        state.cash = notional * (1.0 - rules.fee);
        state.shares = 0.0;
        state.notional += notional;
        state.fees += fee;
        ++state.trades;
        if constexpr (Diagnose) trace->liquidation_fee = fee;
    }
    // Final liquidation replaces the final mark, including its fee.
    const double equity = state.cash + state.shares * bar.close;
    state.peak = std::max(state.peak, equity);
    state.max_drawdown = std::max(state.max_drawdown, 1.0 - equity / state.peak);
    if constexpr (Diagnose) {
        trace->equity = equity;
        trace->after_close = state;
    }
}

template<class Mapping, bool Diagnose>
void run(std::span<const Bar> bars, std::span<const Config> configs,
         std::span<const double> buffer, std::size_t windows, std::size_t first,
         Order order, const Rules& rules, std::span<State> states, Trace* traces) {
#ifdef OIR_STRATEGY_MANUAL_INDEX
    // Comparison build: the same dynamic extents and layout, written by hand.
    // No restrict, static dimensions, cached offsets or altered account lifetime.
    const auto feature = [data = buffer.data(), rows = bars.size(), windows]
                         (std::size_t t, std::size_t w) -> const double& {
        if constexpr (std::is_same_v<Mapping, std::layout_left>)
            return data[t + rows * w];
        else
            return data[t * windows + w];
    };
#else
    const std::mdspan<const double, std::dextents<std::size_t, 2>, Mapping>
        features(buffer.data(), bars.size(), windows);
    const auto feature = [&features](std::size_t t, std::size_t w) -> const double& {
        return features[t, w];
    };
#endif
    const auto eligible = bars.size() > first ? bars.size() - first : 0;
    if (order == Order::strategy) {
        for (std::size_t s = 0; s < configs.size(); ++s) {
            auto state = states[s];
            const auto config = configs[s];
            for (std::size_t t = first; t < bars.size(); ++t) {
                Trace* trace = nullptr;
                if constexpr (Diagnose) trace = &traces[s * eligible + t - first];
                const bool target = feature(t - 1, config.fast) > feature(t - 1, config.slow);
                step<Diagnose>(state, target, bars[t], t + 1 == bars.size(), rules, trace);
            }
            states[s] = state;
        }
    } else {
        for (std::size_t t = first; t < bars.size(); ++t) {
            for (std::size_t s = 0; s < configs.size(); ++s) {
                Trace* trace = nullptr;
                if constexpr (Diagnose) trace = &traces[s * eligible + t - first];
                const auto config = configs[s];
                const bool target = feature(t - 1, config.fast) > feature(t - 1, config.slow);
                step<Diagnose>(states[s], target, bars[t], t + 1 == bars.size(), rules, trace);
            }
        }
    }
}

template<bool Diagnose>
void dispatch(std::span<const Bar> bars, std::span<const Config> configs,
              std::span<const double> features, std::size_t windows,
              std::size_t first, Layout layout, Order order, const Rules& rules,
              std::span<State> states, Trace* traces) {
    if (layout == Layout::history)
        run<std::layout_left, Diagnose>(bars, configs, features, windows, first, order, rules, states, traces);
    else
        run<std::layout_right, Diagnose>(bars, configs, features, windows, first, order, rules, states, traces);
}
} // namespace

void validate(std::span<const Bar> bars, std::span<const std::size_t> spans,
              const Rules& rules, bool allow_empty) {
    if (!std::isfinite(rules.capital) || rules.capital <= 0 ||
        !std::isfinite(rules.fee) || rules.fee < 0 || rules.fee >= 1)
        throw std::invalid_argument("capital must be positive; fee must be in [0,1)");
    if (bars.empty() || spans.empty()) throw std::invalid_argument("bars and spans must be nonempty");
    for (std::size_t w = 0; w < spans.size(); ++w)
        if (spans[w] < 2 || (w != 0 && spans[w] <= spans[w-1]))
            throw std::invalid_argument("spans must be strictly increasing integers >= 2");
    if (!allow_empty && bars.size() <= spans.back())
        throw std::invalid_argument("no eligible bars after common warm-up");
    for (std::size_t t = 0; t < bars.size(); ++t) {
        const auto& b = bars[t];
        if (!std::isfinite(b.open) || !std::isfinite(b.close) || b.open <= 0 || b.close <= 0)
            throw std::invalid_argument("prices must be finite and positive");
        if (t != 0 && b.timestamp <= bars[t-1].timestamp)
            throw std::invalid_argument("timestamps must be strictly increasing");
    }
    product(bars.size(), spans.size());
}

std::vector<Config> configurations(std::size_t windows, std::size_t count) {
    const auto maximum = windows < 2 ? 0 : product(windows, windows - 1) / 2;
    if (count > maximum) throw std::invalid_argument("configuration count exceeds fast<slow pairs");
    std::vector<Config> result;
    result.reserve(count);
    for (std::size_t fast = 0; fast < windows && result.size() < count; ++fast)
        for (std::size_t slow = fast + 1; slow < windows && result.size() < count; ++slow)
            result.push_back({fast, slow});
    return result;
}

std::vector<double> prepare_history(std::span<const Bar> bars,
                                    std::span<const std::size_t> spans) {
    std::vector<double> result(product(bars.size(), spans.size()));
    for (std::size_t w = 0; w < spans.size(); ++w) {
        const double alpha = 2.0 / (static_cast<double>(spans[w]) + 1.0);
        double previous = bars.front().close;
        result[w * bars.size()] = previous;
        for (std::size_t t = 1; t < bars.size(); ++t) {
            previous = alpha * bars[t].close + (1.0 - alpha) * previous;
            result[w * bars.size() + t] = previous;
        }
    }
    return result;
}

std::vector<double> materialize(std::vector<double>&& history, std::size_t bars,
                                std::size_t windows, Layout layout) {
    if (layout == Layout::history) return std::move(history);
    std::vector<double> snapshot(product(bars, windows));
    for (std::size_t t = 0; t < bars; ++t)
        for (std::size_t w = 0; w < windows; ++w)
            snapshot[t * windows + w] = history[w * bars + t];
    // Release canonical scratch before replay; allocation peak is disclosed.
    std::vector<double>().swap(history);
    return snapshot;
}

std::vector<State> initial_states(std::size_t count, const Rules& rules) {
    return std::vector<State>(count, State{rules.capital, 0.0, rules.capital, 0.0, 0.0, 0.0, 0});
}
std::vector<Summary> summarize(std::span<const State> states, const Rules& rules) {
    std::vector<Summary> result;
    result.reserve(states.size());
    for (const auto& s : states) {
        if (!std::isfinite(s.cash) || !std::isfinite(s.notional) || !std::isfinite(s.fees) ||
            !std::isfinite(s.peak) || !std::isfinite(s.max_drawdown) || s.cash < 0 || s.shares != 0)
            throw std::runtime_error("nonfinite or unfinished account");
        result.push_back({s.cash, s.cash / rules.capital - 1.0, s.trades,
                          s.notional / rules.capital, s.max_drawdown, s.fees});
    }
    return result;
}

void replay(std::span<const Bar> bars, std::span<const Config> configs,
            std::span<const double> features, std::size_t windows,
            std::size_t first, Layout layout, Order order, const Rules& rules,
            std::span<State> states) {
    dispatch<false>(bars, configs, features, windows, first, layout, order, rules, states, nullptr);
}
std::vector<Trace> trace_replay(std::span<const Bar> bars,
            std::span<const Config> configs, std::span<const double> features,
            std::size_t windows, std::size_t first, Layout layout, Order order,
            const Rules& rules, std::span<State> states) {
    const auto eligible = bars.size() > first ? bars.size() - first : 0;
    std::vector<Trace> traces(product(configs.size(), eligible));
    dispatch<true>(bars, configs, features, windows, first, layout, order, rules, states, traces.data());
    return traces;
}
} // namespace strategy
