// Same logical [bar, window] values, stored in two different physical orders.
#include <array>
#include <cstddef>
#include <iostream>
#include <mdspan>
#include <version>

template<class Layout>
using FeatureView = std::mdspan<const double,
                              std::dextents<std::size_t, 2>, Layout>;

int main() {
    constexpr std::size_t bars = 3;
    constexpr std::size_t windows = 2;
    // Invented feature values: column A is 10,11,12; column B is 20,21,22.
    const std::array<double, 6> histories{10, 11, 12, 20, 21, 22};
    const std::array<double, 6> snapshots{10, 20, 11, 21, 12, 22};
    const FeatureView<std::layout_left> history(histories.data(), bars, windows);
    const FeatureView<std::layout_right> snapshot(snapshots.data(), bars, windows);

    for (std::size_t t = 0; t < bars; ++t) {
        for (std::size_t w = 0; w < windows; ++w) {
            const double expected = static_cast<double>((w + 1) * 10 + t);
            if (history[t, w] != expected || snapshot[t, w] != expected) {
                std::cerr << "Logical values differ\n";
                return 1;
            }
        }
    }
    if (history.stride(0) != 1 || history.stride(1) != bars ||
        snapshot.stride(0) != windows || snapshot.stride(1) != 1) {
        std::cerr << "Unexpected strides\n";
        return 1;
    }

    // A different view does not rearrange its backing buffer.
    const FeatureView<std::layout_right> wrong(histories.data(), bars, windows);
    if (wrong[1, 0] != 12 || history[1, 0] != 11) {
        std::cerr << "Reinterpretation counterexample failed\n";
        return 1;
    }
    const FeatureView<std::layout_left> empty(histories.data(), 0, windows);
    const FeatureView<std::layout_right> one(snapshots.data(), 1, 1);
    if (!empty.empty() || empty.mapping().required_span_size() != 0 || one[0, 0] != 10) {
        std::cerr << "Boundary check failed\n";
        return 1;
    }

    std::cout << "{\"cpp\":" << __cplusplus
              << ",\"mdspan\":" << __cpp_lib_mdspan
              << ",\"logical_values_checked\":6"
              << ",\"history_strides\":[1,3],\"snapshot_strides\":[2,1]"
              << ",\"reinterpretation_counterexample\":true"
              << ",\"boundary_checks\":true,\"timed\":false}\n";
}
