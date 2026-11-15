#include "barrier.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <experimental/simd>
#include <limits>
#include <stdexcept>

namespace barrier {
namespace sx = std::experimental;
using V = sx::native_simd<double>;
using M = V::mask_type;
constexpr auto W = V::size();
std::size_t native_width() { return W; }

void validate(const Input& in, const Contract& c) {
    if (!in.steps || in.paths > std::numeric_limits<std::size_t>::max() / in.steps ||
        in.factors.size() != in.paths * in.steps)
        throw std::invalid_argument("invalid dimensions or factor count");
    if (in.layout != Layout::path_major && in.layout != Layout::step_major)
        throw std::invalid_argument("invalid layout");
    if (!(c.spot > 0) || !std::isfinite(c.spot) || c.strike < 0 || !std::isfinite(c.strike) ||
        !(c.barrier > 0) || std::isnan(c.barrier) || !(c.discount > 0) || !std::isfinite(c.discount))
        throw std::invalid_argument("invalid contract (positive infinity allowed only for barrier)");
    for (const auto factor : in.factors)
        if (!(factor > 0) || !std::isfinite(factor))
            throw std::invalid_argument("nonpositive/nonfinite multiplier");
    if (c.spot >= c.barrier) return;
    for (std::size_t p = 0; p < in.paths; ++p) {
        auto s = c.spot;
        for (std::size_t t = 0; t < in.steps; ++t) {
            s *= in.at(p, t);
            if (!std::isfinite(s) || s == 0)
                throw std::range_error("reachable stock overflow/underflow to zero");
            if (s >= c.barrier) break;
        }
        if (s < c.barrier && !std::isfinite(c.discount * std::max(s - c.strike, 0.0)))
            throw std::range_error("payoff overflow");
    }
}

template<Layout L>
inline double factor(const Input& in, std::size_t p, std::size_t t) {
    if constexpr (L == Layout::path_major) return in.factors[p * in.steps + t];
    else return in.factors[t * in.paths + p];
}
template<bool D>
inline void finished(Diagnostics* d, std::size_t p, std::size_t t, bool hit) {
    if constexpr (D) {
        d->lifetimes[p] = t;
        d->knocked_out[p] = static_cast<std::uint8_t>(hit);
    }
}

template<Layout L, bool D>
void scalar(const Input& in, const Contract& c, std::span<double> out, Diagnostics* d) {
    for (std::size_t p = 0; p < in.paths; ++p) {
        double s = c.spot;
        std::size_t t = 0;
        bool hit = false;
        for (; t < in.steps;) {
            s *= factor<L>(in, p, t++);
            if (s >= c.barrier) { hit = true; break; }
        }
        out[p] = hit ? 0.0 : c.discount * std::max(s - c.strike, 0.0);
        finished<D>(d, p, t, hit);
        if constexpr (D) { d->useful_lane_steps += t; d->available_lane_steps += t; }
    }
}

template<Layout L, bool D>
void fixed(const Input& in, const Contract& c, std::span<double> out, Diagnostics* d) {
    for (std::size_t base = 0; base < in.paths; base += W) {
        V s(c.spot);
        M live(false);
        const auto count = std::min(W, in.paths - base);
        for (std::size_t lane = 0; lane < count; ++lane) { live[lane] = true; out[base + lane] = 0; }
        std::size_t t = 0;
        while (t < in.steps && sx::any_of(live)) {
            if constexpr (D) { d->useful_lane_steps += sx::popcount(live); d->available_lane_steps += W; }
            V f(1.0);
            if constexpr (L == Layout::step_major) {
                sx::where(live, f).copy_from(in.factors.data() + t * in.paths + base, sx::element_aligned);
            } else {
                for (std::size_t lane = 0; lane < W; ++lane)
                    if (live[lane]) f[lane] = factor<L>(in, base + lane, t);
            }
            s *= f;
            ++t;
            const M hit = live && (s >= V(c.barrier));
            if constexpr (D)
                for (std::size_t lane = 0; lane < count; ++lane)
                    if (hit[lane]) finished<D>(d, base + lane, t, true);
            live &= !hit;
        }
        for (std::size_t lane = 0; lane < count; ++lane) {
            if (live[lane]) {
                out[base + lane] = c.discount * std::max(double(s[lane]) - c.strike, 0.0);
                finished<D>(d, base + lane, t, false);
            }
        }
    }
}

template<Layout L, bool D>
void refill(const Input& in, const Contract& c, std::span<double> out, Diagnostics* d) {
    std::array<std::size_t, W> ids{}, dates{};
    V s(c.spot);
    M live(false);
    std::size_t next = 0;
    for (std::size_t lane = 0; lane < W && next < in.paths; ++lane) {
        ids[lane] = next++;
        live[lane] = true;
    }
    while (sx::any_of(live)) {
        if constexpr (D) { d->useful_lane_steps += sx::popcount(live); d->available_lane_steps += W; }
        V f(1.0);
        for (std::size_t lane = 0; lane < W; ++lane)
            if (live[lane]) f[lane] = factor<L>(in, ids[lane], dates[lane]++);
        s *= f;
        const M hit = live && (s >= V(c.barrier));
        for (std::size_t lane = 0; lane < W; ++lane) {
            if (live[lane] && (hit[lane] || dates[lane] == in.steps)) {
                out[ids[lane]] = hit[lane] ? 0.0 : c.discount * std::max(double(s[lane]) - c.strike, 0.0);
                finished<D>(d, ids[lane], dates[lane], hit[lane]);
                if (next < in.paths) {
                    ids[lane] = next++;
                    dates[lane] = 0;
                    s[lane] = c.spot;
                    if constexpr (D) ++d->replacements;
                } else {
                    live[lane] = false;
                }
            }
        }
    }
}

template<Layout L, bool D>
double dispatch(const Input& in, const Contract& c, Method method, std::span<double> out, Diagnostics* d) {
    if (out.size() != in.paths) throw std::invalid_argument("output count differs from paths");
    if (method != Method::scalar && method != Method::fixed && method != Method::refill)
        throw std::invalid_argument("invalid method");
    if (c.spot >= c.barrier) {
        std::fill(out.begin(), out.end(), 0.0);
        if constexpr (D) std::fill(d->knocked_out.begin(), d->knocked_out.end(), 1);
    } else {
        switch (method) {
            case Method::scalar: scalar<L,D>(in, c, out, d); break;
            case Method::fixed: fixed<L,D>(in, c, out, d); break;
            case Method::refill: refill<L,D>(in, c, out, d); break;
        }
    }
    double sum = 0;
    for (const auto x : out) sum += x;
    if (!std::isfinite(sum)) throw std::range_error("aggregate overflow");
    return in.paths ? sum / static_cast<double>(in.paths) : 0.0;
}
double evaluate(const Input& in, const Contract& c, Method m, std::span<double> out) {
    return in.layout == Layout::path_major ? dispatch<Layout::path_major,false>(in,c,m,out,nullptr)
                                          : dispatch<Layout::step_major,false>(in,c,m,out,nullptr);
}
double diagnose(const Input& in, const Contract& c, Method m, std::span<double> out, Diagnostics& d) {
    d = {};
    d.lifetimes.resize(in.paths);
    d.knocked_out.resize(in.paths);
    return in.layout == Layout::path_major ? dispatch<Layout::path_major,true>(in,c,m,out,&d)
                                          : dispatch<Layout::step_major,true>(in,c,m,out,&d);
}
}
