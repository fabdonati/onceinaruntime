#include "replay.hpp"

#include <algorithm>
#include <cstring>
#include <limits>
#include <queue>
#include <random>
#include <stdexcept>
#include <utility>

namespace replay {
namespace {
std::pair<std::size_t, std::size_t> bounds(const Stream& stream, Range range) {
    if (range.begin > range.end) {
        throw std::invalid_argument("range begin exceeds end");
    }
    return {static_cast<std::size_t>(std::min<std::uint64_t>(range.begin, stream.count)),
            static_cast<std::size_t>(std::min<std::uint64_t>(range.end, stream.count))};
}

void append(const Stream& stream, std::size_t position, std::vector<std::byte>& output) {
    const auto record = stream.record(position);
    output.insert(output.end(), record.begin(), record.end());
}
} // namespace

Header Stream::header(std::size_t position) const {
    Header result{};
    const auto data = record(position);
    std::memcpy(&result, data.data(), sizeof(result));
    return result;
}

std::span<const std::byte> Stream::record(std::size_t position) const {
    if (position >= count) {
        throw std::out_of_range("record position");
    }
    return std::span<const std::byte>{bytes}.subspan(position * stride, stride);
}

Stream generate(std::size_t count, std::uint32_t topics, std::uint32_t payload_bytes,
                std::uint64_t seed, bool hot_topic) {
    if (topics == 0) {
        throw std::invalid_argument("topic count must be positive");
    }
    const auto stride = sizeof(Header) + static_cast<std::size_t>(payload_bytes);
    if (count > std::numeric_limits<std::size_t>::max() / stride) {
        throw std::length_error("message storage size overflow");
    }
    Stream stream{count, topics, stride, std::vector<std::byte>(count * stride)};
    std::mt19937_64 random{seed};
    for (std::size_t position = 0; position < count; ++position) {
        const auto draw = random();
        const auto topic = hot_topic && draw % 10 < 8
                               ? 0U : static_cast<std::uint32_t>(random() % topics);
        const Header header{position, topic, payload_bytes};
        auto* destination = stream.bytes.data() + position * stride;
        std::memcpy(destination, &header, sizeof(header));
        for (std::size_t byte = 0; byte < payload_bytes; ++byte) {
            destination[sizeof(Header) + byte] =
                static_cast<std::byte>((seed + position * 17 + byte * 31) & 0xffU);
        }
    }
    return stream;
}

Selection::Selection(std::uint32_t topic_count, std::span<const std::uint32_t> requested)
    : bitmap(topic_count, 0) {
    for (const auto topic : requested) {
        if (topic < topic_count && bitmap[topic] == 0) {
            bitmap[topic] = 1;
            topics.push_back(topic);
        }
    }
    std::sort(topics.begin(), topics.end());
}

Index build_index(const Stream& stream) {
    Index index(stream.topics);
    for (std::size_t position = 0; position < stream.count; ++position) {
        index[stream.header(position).topic].push_back(position);
    }
    return index;
}

std::size_t index_capacity_bytes(const Index& index) {
    std::size_t bytes = sizeof(Index) + index.capacity() * sizeof(Index::value_type);
    for (const auto& positions : index) {
        bytes += positions.capacity() * sizeof(std::size_t);
    }
    return bytes;
}

Stats scan(const Stream& stream, const Selection& selection, Range range,
           std::vector<std::byte>& output) {
    const auto [begin, end] = bounds(stream, range);
    output.clear();
    Stats stats{};
    for (auto position = begin; position < end; ++position) {
        ++stats.examined;
        if (selection.bitmap[stream.header(position).topic] != 0) {
            append(stream, position, output);
            ++stats.returned;
        }
    }
    return stats;
}

Stats indexed(const Stream& stream, const Index& index, const Selection& selection,
              Range range, std::vector<std::byte>& output) {
    const auto [begin, end] = bounds(stream, range);
    output.clear();
    struct Cursor {
        std::size_t position;
        std::uint32_t topic;
        std::size_t offset;
    };
    const auto later = [](const Cursor& left, const Cursor& right) {
        return left.position > right.position;
    };
    std::vector<Cursor> storage;
    storage.reserve(selection.topics.size());
    std::priority_queue<Cursor, std::vector<Cursor>, decltype(later)> heap(later, std::move(storage));
    for (const auto topic : selection.topics) {
        const auto& positions = index[topic];
        const auto found = std::lower_bound(positions.begin(), positions.end(), begin);
        if (found != positions.end() && *found < end) {
            heap.push({*found, topic, static_cast<std::size_t>(found - positions.begin())});
        }
    }
    Stats stats{};
    while (!heap.empty()) {
        const auto cursor = heap.top();
        heap.pop();
        ++stats.examined;
        ++stats.returned;
        append(stream, cursor.position, output);
        const auto& positions = index[cursor.topic];
        const auto next = cursor.offset + 1;
        if (next < positions.size() && positions[next] < end) {
            heap.push({positions[next], cursor.topic, next});
        }
    }
    return stats;
}

std::uint64_t checksum(std::span<const std::byte> bytes) {
    std::uint64_t value = 14695981039346656037ULL;
    for (const auto byte : bytes) {
        value ^= std::to_integer<std::uint8_t>(byte);
        value *= 1099511628211ULL;
    }
    return value;
}
} // namespace replay
