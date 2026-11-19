#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace barrier {
enum class Layout { path_major, step_major };
enum class Method { scalar, fixed, refill };
struct Contract { double spot{100}, strike{100}, barrier{120}, discount{1}; };
struct Input {
    std::span<const double> factors;
    std::size_t paths{}, steps{};
    Layout layout{Layout::path_major};
    double at(std::size_t path, std::size_t step) const {
        return factors[layout == Layout::path_major ? path * steps + step : step * paths + path];
    }
};
struct Diagnostics {
    std::vector<std::uint64_t> lifetimes;
    std::vector<std::uint8_t> knocked_out;
    std::uint64_t useful_lane_steps{}, available_lane_steps{}, replacements{};
};
std::size_t native_width();
// Validates all factors and the reachable stock-price range outside timing.
void validate(const Input&, const Contract&);
// Precondition: validated input/contract and output.size() == input.paths.
// Every payoff is overwritten; aggregation uses ascending path-ID order.
double evaluate(const Input&, const Contract&, Method, std::span<double> output);
// Same algorithms instantiated with instrumentation, never used for timing.
double diagnose(const Input&, const Contract&, Method, std::span<double>, Diagnostics&);
}
