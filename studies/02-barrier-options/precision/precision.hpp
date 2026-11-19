#pragma once
#include "barrier.hpp"

namespace barrier::precision {
struct Contract { float spot{100}, strike{100}, barrier{120}, discount{1}; };
struct Input {
    std::span<const float> factors;
    std::size_t paths{}, steps{};
    Layout layout{Layout::path_major};
};
std::size_t native_width();
void validate(const Input&, const Contract&);
// Validated input; every float payoff is written, then reduced in double order.
double evaluate(const Input&, const Contract&, Method, std::span<float>);
double diagnose(const Input&, const Contract&, Method, std::span<float>, Diagnostics&);
}
