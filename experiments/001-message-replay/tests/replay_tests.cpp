#include "replay.hpp"

#include <algorithm>
#include <cstring>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename Function>
void invalid(Function function) {
    try {
        function();
    } catch (const std::invalid_argument&) {
        return;
    }
    throw std::runtime_error("expected invalid_argument");
}

void verify(const replay::Stream& stream, const std::vector<std::uint32_t>& topics,
            replay::Range range, const std::vector<std::size_t>& expected_positions) {
    std::vector<std::byte> expected;
    for (const auto position : expected_positions) {
        const auto first = stream.bytes.begin() + static_cast<std::ptrdiff_t>(position * stream.stride);
        expected.insert(expected.end(), first, first + static_cast<std::ptrdiff_t>(stream.stride));
    }
    const replay::Selection selection(stream.topics, topics);
    const auto index = replay::build_index(stream);
    std::vector<std::byte> scan_output{std::byte{99}};
    std::vector<std::byte> index_output{std::byte{99}};
    const auto scan_stats = replay::scan(stream, selection, range, scan_output);
    const auto index_stats = replay::indexed(stream, index, selection, range, index_output);
    require(scan_output == expected, "scan content or order");
    require(index_output == expected, "index content or order");
    require(scan_stats.returned == expected_positions.size(), "scan count");
    require(index_stats.returned == expected_positions.size(), "index count");
    require(index_stats.examined == expected_positions.size(), "index record visits");
    require(scan_stats.examined == std::min<std::uint64_t>(range.end, stream.count)
                                     - std::min<std::uint64_t>(range.begin, stream.count),
            "scan record visits");
}

void fixed_cases() {
    // Handcrafted interleaving and unaligned 19-byte records, independent of generation.
    const std::vector<std::uint32_t> topics{2, 0, 2, 1, 0, 1};
    replay::Stream stream{topics.size(), 3, sizeof(replay::Header) + 3, {}};
    stream.bytes.resize(stream.count * stream.stride);
    for (std::size_t position = 0; position < stream.count; ++position) {
        const replay::Header header{position, topics[position], 3};
        auto* record = stream.bytes.data() + position * stream.stride;
        std::memcpy(record, &header, sizeof(header));
        for (std::size_t byte = 0; byte < 3; ++byte) {
            record[sizeof(header) + byte] = static_cast<std::byte>(position * 10 + byte);
        }
    }
    verify(stream, {}, {0, 6}, {});
    verify(stream, {0, 1, 2}, {0, 6}, {0, 1, 2, 3, 4, 5});
    verify(stream, {2, 0, 2, 99}, {0, 6}, {0, 1, 2, 4});
    verify(stream, {0}, {1, 4}, {1});
    verify(stream, {1}, {3, 4}, {3});
    verify(stream, {1}, {5, 6}, {5});
    verify(stream, {0, 1, 2}, {2, 2}, {});
    verify(stream, {99}, {0, 6}, {});
    verify(stream, {1}, {5, std::numeric_limits<std::uint64_t>::max()}, {5});
    verify(stream, {0}, {10, 20}, {});
    verify(replay::generate(0, 3, 0, 0), {0, 1}, {0, 10}, {});
    verify(replay::generate(1, 1, 0, 0), {0}, {0, 1}, {0});
    std::vector<std::byte> output;
    const replay::Selection selection(3, topics);
    invalid([&] { (void)replay::scan(stream, selection, {3, 2}, output); });
    const auto index = replay::build_index(stream);
    invalid([&] { (void)replay::indexed(stream, index, selection, {3, 2}, output); });
    invalid([] { (void)replay::generate(1, 0, 0, 0); });
    try {
        (void)replay::generate(std::numeric_limits<std::size_t>::max(), 1, 1, 0);
        throw std::runtime_error("expected overflow rejection");
    } catch (const std::length_error&) {
    }
}

void randomized_cases() {
    // Fixed seeds are printed on failure and retained here for exact reproduction.
    for (const std::uint64_t seed : {1ULL, 42ULL, 20261101ULL, 0xfab123ULL}) {
        std::mt19937_64 random(seed);
        for (std::size_t trial = 0; trial < 100; ++trial) {
            try {
                const auto count = static_cast<std::size_t>(random() % 300);
                const auto topic_count = static_cast<std::uint32_t>(1 + random() % 20);
                const auto payload = static_cast<std::uint32_t>(random() % 65);
                const auto stream = replay::generate(count, topic_count, payload, seed, trial % 2 != 0);
                require(stream.bytes == replay::generate(count, topic_count, payload, seed, trial % 2 != 0).bytes,
                        "generation reproducibility");
                for (std::size_t position = 0; position < count; ++position) {
                    const auto header = stream.header(position);
                    require(header.sequence == position && header.topic < topic_count
                                && header.payload_bytes == payload, "generated header");
                    for (std::size_t byte = 0; byte < payload; ++byte) {
                        require(stream.record(position)[sizeof(header) + byte]
                                    == static_cast<std::byte>((seed + position * 17 + byte * 31) & 0xffU),
                                "generated payload");
                    }
                }
                std::vector<std::uint32_t> selected;
                for (std::size_t i = 0, n = random() % 30; i < n; ++i) {
                    selected.push_back(static_cast<std::uint32_t>(random() % (topic_count + 3)));
                }
                auto begin = random() % (count + 5);
                auto end = random() % (count + 5);
                if (begin > end) { std::swap(begin, end); }
                // Independent membership oracle with direct per-record expectations.
                std::vector<std::size_t> expected;
                for (std::size_t position = 0; position < count; ++position) {
                    const auto topic = stream.header(position).topic;
                    if (position >= begin && position < end
                        && std::find(selected.begin(), selected.end(), topic) != selected.end()) {
                        expected.push_back(position);
                    }
                }
                verify(stream, selected, {begin, end}, expected);
            } catch (const std::exception& error) {
                throw std::runtime_error("seed=" + std::to_string(seed) + " trial="
                                         + std::to_string(trial) + ": " + error.what());
            }
        }
    }
}
} // namespace

int main() {
    try {
        fixed_cases();
        randomized_cases();
        std::cout << "Fixed cases and 400 randomized cases passed; seeds 1, 42, 20261101, 16429347\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
