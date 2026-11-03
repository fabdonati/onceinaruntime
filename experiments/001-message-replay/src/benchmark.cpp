#include "replay.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {
using Clock = std::chrono::steady_clock;
static_assert(Clock::is_steady);
std::int64_t elapsed(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
}

struct Observation {
    std::uint64_t repetition;
    int order;
    bool use_index;
    std::int64_t nanoseconds;
    replay::Stats stats;
    std::uint64_t hash;
};

std::uint32_t u32(std::uint64_t value) {
    if (value > std::numeric_limits<std::uint32_t>::max()) {
        throw std::invalid_argument("option exceeds uint32 range");
    }
    return static_cast<std::uint32_t>(value);
}
} // namespace

int main(int argc, char** argv) {
    try {
        std::map<std::string, std::uint64_t> options{
            {"messages", 100000}, {"topics", 64}, {"payload-bytes", 48},
            {"selected-topics", 1}, {"selection-offset", 0}, {"seed", 20261101},
            {"begin", 0}, {"end", std::numeric_limits<std::uint64_t>::max()},
            {"hot-topic", 0}, {"warmups", 2}, {"repetitions", 8}};
        std::vector<std::string> seen;
        for (int i = 1; i < argc; i += 2) {
            const std::string name = argv[i];
            if (i + 1 >= argc || !name.starts_with("--") || !options.contains(name.substr(2))
                || std::find(seen.begin(), seen.end(), name) != seen.end()) {
                throw std::invalid_argument("unknown, duplicate or incomplete option: " + name);
            }
            seen.push_back(name);
            const std::string_view value = argv[i + 1];
            std::uint64_t parsed = 0;
            const auto result = std::from_chars(value.data(), value.data() + value.size(), parsed);
            if (result.ec != std::errc{} || result.ptr != value.data() + value.size()) {
                throw std::invalid_argument("expected unsigned integer for " + name);
            }
            options[name.substr(2)] = parsed;
        }
        const auto topics = u32(options.at("topics"));
        const auto payload = u32(options.at("payload-bytes"));
        const auto selected = u32(options.at("selected-topics"));
        const auto count = options.at("messages");
        if (count > std::numeric_limits<std::size_t>::max() || topics == 0 || selected > topics
            || options.at("repetitions") == 0 || options.at("hot-topic") > 1) {
            throw std::invalid_argument("invalid count, topics, selection, repetitions or distribution");
        }
        const replay::Range range{options.at("begin"), options.at("end")};
        if (range.begin > range.end) { throw std::invalid_argument("range begin exceeds end"); }
        auto start = Clock::now();
        const auto stream = replay::generate(static_cast<std::size_t>(count), topics, payload,
                                            options.at("seed"), options.at("hot-topic") == 1);
        const auto stream_build_ns = elapsed(start, Clock::now());
        start = Clock::now();
        const auto index = replay::build_index(stream);
        const auto index_build_ns = elapsed(start, Clock::now());

        std::vector<std::uint32_t> requested;
        for (std::uint32_t i = 0; i < selected; ++i) {
            requested.push_back(static_cast<std::uint32_t>((options.at("selection-offset") % topics + i) % topics));
        }
        const replay::Selection selection(topics, requested);
        std::vector<std::byte> reference;
        const auto reference_stats = replay::scan(stream, selection, range, reference);
        std::vector<std::byte> outputs[2];
        for (auto& output : outputs) { output.reserve(reference.size()); }
        const auto expected_hash = replay::checksum(reference);

        const auto query = [&](bool use_index, std::vector<std::byte>& output) {
            return use_index ? replay::indexed(stream, index, selection, range, output)
                             : replay::scan(stream, selection, range, output);
        };
        const auto validate = [&](const std::vector<std::byte>& output, replay::Stats stats) {
            const auto hash = replay::checksum(output);
            if (output != reference || hash != expected_hash || stats.returned != reference_stats.returned) {
                throw std::runtime_error("retrieval diverged from reference");
            }
            return hash;
        };
        for (std::uint64_t i = 0; i < options.at("warmups"); ++i) {
            for (int order = 0; order < 2; ++order) {
                const auto use_index = (i + static_cast<std::uint64_t>(order)) % 2 != 0;
                auto& output = outputs[use_index ? 1 : 0];
                (void)validate(output, query(use_index, output));
            }
        }

        std::vector<std::int64_t> clock_samples;
        clock_samples.reserve(1000);
        for (int i = 0; i < 1000; ++i) {
            start = Clock::now();
            clock_samples.push_back(elapsed(start, Clock::now()));
        }
        std::sort(clock_samples.begin(), clock_samples.end());
        std::vector<Observation> observations;
        for (std::uint64_t repetition = 0; repetition < options.at("repetitions"); ++repetition) {
            for (int order = 0; order < 2; ++order) {
                const auto use_index = (repetition + static_cast<std::uint64_t>(order)) % 2 != 0;
                auto& output = outputs[use_index ? 1 : 0];
                start = Clock::now();
                const auto stats = query(use_index, output);
                const auto ns = elapsed(start, Clock::now());
                const auto hash = validate(output, stats); // Intentionally outside timing.
                observations.push_back({repetition, order, use_index, ns, stats, hash});
            }
        }
        std::cout << "{\n  \"schema_version\": 1,\n  \"preliminary\": true,\n  \"parameters\": {";
        bool first = true;
        for (const auto& [name, value] : options) {
            if (!first) { std::cout << ','; }
            first = false;
            std::cout << '\"' << name << "\":" << value;
        }
        std::cout << "},\n  \"stream_build_ns\":" << stream_build_ns
                  << ",\n  \"index_build_ns\":" << index_build_ns
                  << ",\n  \"stream_capacity_bytes\":" << sizeof(replay::Stream) + stream.bytes.capacity()
                  << ",\n  \"index_capacity_bytes\":" << replay::index_capacity_bytes(index)
                  << ",\n  \"reference_and_output_capacity_bytes\":"
                  << reference.capacity() + outputs[0].capacity() + outputs[1].capacity()
                  << ",\n  \"timer_pair_samples\":1000,\n  \"timer_pair_min_ns\":" << clock_samples.front()
                  << ",\n  \"timer_pair_median_ns\":" << clock_samples[500]
                  << ",\n  \"observations\":[\n";
        first = true;
        for (const auto& observation : observations) {
            if (!first) { std::cout << ",\n"; }
            first = false;
            std::cout << "    {\"repetition\":" << observation.repetition
                      << ",\"order\":" << observation.order << ",\"algorithm\":\""
                      << (observation.use_index ? "indexed" : "scan") << "\",\"query_ns\":"
                      << observation.nanoseconds << ",\"messages_examined\":" << observation.stats.examined
                      << ",\"returned\":" << observation.stats.returned << ",\"bytes_returned\":"
                      << observation.stats.returned * stream.stride << ",\"checksum\":" << observation.hash << '}';
        }
        std::cout << "\n  ]\n}\n";
    } catch (const std::exception& error) {
        std::cerr << "replay_bench: " << error.what() << '\n';
        return 1;
    }
}
