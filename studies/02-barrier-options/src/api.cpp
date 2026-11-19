#include "barrier.hpp"
#include <exception>

// Small Python bridge for a complete in-process generation + valuation interval.
// Inputs must pass the same validation gate before benchmark use. No exceptions cross C.
extern "C" int barrier_evaluate(const double* factors, std::size_t paths, std::size_t steps,
                               int layout, int method, double limit, double discount,
                               double* output, double* price) noexcept {
    try {
        const barrier::Input in{{factors, paths * steps}, paths, steps, static_cast<barrier::Layout>(layout)};
        *price = barrier::evaluate(in, {100,100,limit,discount}, static_cast<barrier::Method>(method), {output,paths});
        return 0;
    } catch (const std::exception&) { return 1; }
}
