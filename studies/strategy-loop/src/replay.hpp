#pragma once

#include <cstddef>
#include <cstdint>
#include <mdspan>
#include <span>
#include <vector>

namespace strategy {

struct Bar { std::int64_t timestamp; double open; double close; };
struct Config { std::size_t fast; std::size_t slow; };
enum class Layout { history, snapshot };
enum class Order { strategy, event };
struct Rules { double capital = 1000.0; double fee = 0.0001; };

struct State {
    double cash;
    double shares = 0.0;
    double peak;
    double max_drawdown = 0.0;
    double notional = 0.0;
    double fees = 0.0;
    std::uint64_t trades = 0;
};
struct Summary {
    double final_cash;
    double net_return;
    std::uint64_t trades;
    double turnover;
    double max_drawdown;
    double fees;
};
struct Trace {
    bool target_long;
    int opening_event; // +1 buy, -1 sell, 0 unchanged
    double cash_after_open;
    double shares_after_open;
    double opening_fee;
    double liquidation_fee;
    double equity;
    State after_close;
};

void validate(std::span<const Bar> bars, std::span<const std::size_t> spans,
              const Rules& rules, bool allow_empty);
std::vector<Config> configurations(std::size_t windows, std::size_t count);
std::vector<double> prepare_history(std::span<const Bar> bars,
                                    std::span<const std::size_t> spans);
std::vector<double> materialize(std::vector<double>&& history,
                                std::size_t bars, std::size_t windows, Layout layout);
std::vector<State> initial_states(std::size_t count, const Rules& rules);
std::vector<Summary> summarize(std::span<const State> states, const Rules& rules);

// Inputs have already been validated. There is no allocation or diagnostic work
// in the measured replay. Diagnostic traces use a separate template instantiation.
// The owning feature buffer outlives the read-only mdspan constructed here.
void replay(std::span<const Bar> bars, std::span<const Config> configs,
            std::span<const double> features, std::size_t windows,
            std::size_t first_bar, Layout layout, Order order, const Rules& rules,
            std::span<State> states);
std::vector<Trace> trace_replay(std::span<const Bar> bars,
            std::span<const Config> configs, std::span<const double> features,
            std::size_t windows, std::size_t first_bar, Layout layout, Order order,
            const Rules& rules, std::span<State> states);

} // namespace strategy
