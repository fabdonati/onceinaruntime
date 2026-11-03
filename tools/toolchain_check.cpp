#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <numeric>
#include <span>

int main() {
    constexpr std::array values{1, 2, 3};
    const std::span view{values};
    if (std::accumulate(view.begin(), view.end(), 0) != 6) {
        return 1;
    }
    std::cout << "C++ standard: " << __cplusplus << '\n';
#if defined(_LIBCPP_VERSION)
    std::cout << "libc++: " << _LIBCPP_VERSION << '\n';
#elif defined(__GLIBCXX__)
    std::cout << "libstdc++ date: " << __GLIBCXX__ << '\n';
#endif
    std::cout << "Pointer bits: " << sizeof(void*) * 8 << '\n'
              << "Byte order: "
              << (std::endian::native == std::endian::little ? "little" : "other") << '\n';
}
