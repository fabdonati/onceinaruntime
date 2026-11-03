#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace replay {
struct Header {
    std::uint64_t sequence;
    std::uint32_t topic;
    std::uint32_t payload_bytes;
};
static_assert(sizeof(Header) == 16);

struct Stream {
    std::size_t count;
    std::uint32_t topics;
    std::size_t stride;
    std::vector<std::byte> bytes;
    [[nodiscard]] Header header(std::size_t position) const;
    [[nodiscard]] std::span<const std::byte> record(std::size_t position) const;
};

struct Range {
    std::uint64_t begin;
    std::uint64_t end;
};

// Normalize once for both algorithms. Unknown topics do not match any record.
struct Selection {
    Selection(std::uint32_t topic_count, std::span<const std::uint32_t> requested);
    std::vector<std::uint32_t> topics;
    std::vector<std::uint8_t> bitmap;
};

struct Stats {
    std::uint64_t examined = 0; // Record visits; excludes binary search and heap comparisons.
    std::uint64_t returned = 0;
};

using Index = std::vector<std::vector<std::size_t>>;

[[nodiscard]] Stream generate(std::size_t count, std::uint32_t topics,
                              std::uint32_t payload_bytes, std::uint64_t seed,
                              bool hot_topic = false);
[[nodiscard]] Index build_index(const Stream& stream);
[[nodiscard]] std::size_t index_capacity_bytes(const Index& index);
[[nodiscard]] Stats scan(const Stream& stream, const Selection& selection, Range range,
                         std::vector<std::byte>& output);
[[nodiscard]] Stats indexed(const Stream& stream, const Index& index,
                            const Selection& selection, Range range,
                            std::vector<std::byte>& output);
[[nodiscard]] std::uint64_t checksum(std::span<const std::byte> bytes);
} // namespace replay
