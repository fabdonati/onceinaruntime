#include "replay.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>

namespace {
using Clock = std::chrono::steady_clock;
using strategy::Bar;

template<class Integer> Integer integer(const std::string& value) {
    Integer result{};
    const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
        throw std::invalid_argument("invalid integer: " + value);
    return result;
}
double number(const std::string& value) {
    std::size_t end = 0;
    const double result = std::stod(value, &end);
    if (end != value.size()) throw std::invalid_argument("invalid number: " + value);
    return result;
}
std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream stream(line);
    std::string value;
    while (std::getline(stream, value, ',')) fields.push_back(value);
    if (!line.empty() && line.back() == ',') fields.emplace_back();
    return fields;
}
std::vector<Bar> read_bars(const std::string& name) {
    std::ifstream file(name);
    if (!file) throw std::runtime_error("cannot open bars file");
    std::string line;
    if (!std::getline(file, line)) throw std::invalid_argument("missing CSV header");
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line != "timestamp,open,close") throw std::invalid_argument("expected timestamp,open,close header");
    std::vector<Bar> bars;
    while (std::getline(file, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        const auto fields = split(line);
        if (fields.size() != 3) throw std::invalid_argument("bar must contain three fields");
        bars.push_back({integer<std::int64_t>(fields[0]), number(fields[1]), number(fields[2])});
    }
    if (!file.eof()) throw std::runtime_error("error reading bars file");
    return bars;
}
std::ofstream output(const std::string& name) {
    std::ofstream result(name);
    if (!result) throw std::runtime_error("cannot create output: " + name);
    result.exceptions(std::ios::badbit | std::ios::failbit);
    result << std::setprecision(17);
    return result;
}
auto ns(Clock::time_point from, Clock::time_point to) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(to - from).count();
}
void timer() {
    std::vector<std::int64_t> deltas;
    std::size_t zero = 0;
    for (int i = 0; i < 10000; ++i) {
        const auto a = Clock::now();
        const auto b = Clock::now();
        const auto delta = ns(a, b);
        if (delta > 0) deltas.push_back(delta); else ++zero;
    }
    std::sort(deltas.begin(), deltas.end());
    std::cout << "{\"steady\":" << (Clock::is_steady ? "true" : "false")
              << ",\"pairs\":10000,\"zero_or_negative\":" << zero
              << ",\"minimum_positive_ns\":" << (deltas.empty() ? 0 : deltas.front())
              << ",\"median_positive_ns\":" << (deltas.empty() ? 0 : deltas[deltas.size()/2]) << "}\n";
}
} // namespace

int main(int argc, char** argv) try {
    if (argc == 2 && std::string(argv[1]) == "--timer") { timer(); return 0; }
    std::map<std::string, std::string> args;
    bool diagnose = false, timed = false, allow_empty = false;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (key == "--trace") diagnose = true;
        else if (key == "--time") timed = true;
        else if (key == "--allow-empty") allow_empty = true;
        else {
            if (key != "--bars" && key != "--spans" && key != "--count" && key != "--layout" &&
                key != "--order" && key != "--output" && key != "--capital" && key != "--fee")
                throw std::invalid_argument("unknown argument: " + key);
            if (++i >= argc || !args.emplace(key, argv[i]).second)
                throw std::invalid_argument("missing or duplicate argument: " + key);
        }
    }
    for (const auto* key : {"--bars", "--spans", "--layout", "--order", "--output"})
        if (!args.contains(key)) throw std::invalid_argument(std::string("required: ") + key);
    if (timed && (diagnose || allow_empty)) throw std::invalid_argument("timing excludes traces/empty replay");
#ifndef NDEBUG
    if (timed) throw std::invalid_argument("timing requires a Release build");
#endif
    const auto bars = read_bars(args.at("--bars"));
    std::vector<std::size_t> spans;
    for (const auto& field : split(args.at("--spans"))) spans.push_back(integer<std::size_t>(field));
    const strategy::Rules rules{
        args.contains("--capital") ? number(args.at("--capital")) : 1000.0,
        args.contains("--fee") ? number(args.at("--fee")) : 0.0001};
    strategy::validate(bars, spans, rules, allow_empty);
    const auto maximum = spans.size() * (spans.size() - 1) / 2;
    const auto count = args.contains("--count") ? integer<std::size_t>(args.at("--count")) : maximum;
    if (timed && count == 0) throw std::invalid_argument("timing requires configurations");
    const auto configs = strategy::configurations(spans.size(), count);
    const std::string layout_name = args.at("--layout"), order_name = args.at("--order");
    if (layout_name != "history" && layout_name != "snapshot") throw std::invalid_argument("unknown layout");
    if (order_name != "strategy" && order_name != "event") throw std::invalid_argument("unknown order");
    const auto layout = layout_name == "history" ? strategy::Layout::history : strategy::Layout::snapshot;
    const auto order = order_name == "strategy" ? strategy::Order::strategy : strategy::Order::event;
    const auto eligible = bars.size() > spans.back() ? bars.size() - spans.back() : 0;

    const auto now = [timed] { return timed ? Clock::now() : Clock::time_point{}; };
    const auto start = now();
    auto history = strategy::prepare_history(bars, spans);
    const auto prepared = now();
    const auto features = strategy::materialize(std::move(history), bars.size(), spans.size(), layout);
    const auto laid_out = now();
    auto states = strategy::initial_states(configs.size(), rules);
    const auto set_up = now();
    std::vector<strategy::Trace> traces;
    if (diagnose)
        traces = strategy::trace_replay(bars, configs, features, spans.size(), spans.back(), layout, order, rules, states);
    else
        strategy::replay(bars, configs, features, spans.size(), spans.back(), layout, order, rules, states);
    const auto replayed = now();
    const auto summaries = strategy::summarize(states, rules);
    const auto finished = now();

    const auto prefix = args.at("--output");
    auto summary = output(prefix + ".summary.csv");
    summary << "config,fast,slow,final_cash,net_return,trades,turnover,max_drawdown,fees\n";
    for (std::size_t s = 0; s < configs.size(); ++s) {
        const auto& r = summaries[s];
        summary << s << ',' << spans[configs[s].fast] << ',' << spans[configs[s].slow] << ','
                << r.final_cash << ',' << r.net_return << ',' << r.trades << ','
                << r.turnover << ',' << r.max_drawdown << ',' << r.fees << '\n';
    }
    summary.close();
    if (diagnose) {
        auto file = output(prefix + ".features.csv");
        file << "bar,window,span,value\n";
        for (std::size_t t = 0; t < bars.size(); ++t)
            for (std::size_t w = 0; w < spans.size(); ++w)
                file << t << ',' << w << ',' << spans[w] << ','
                     << features[layout == strategy::Layout::history ? w * bars.size() + t : t * spans.size() + w] << '\n';
        file.close();
        auto trace = output(prefix + ".trace.csv");
        trace << "config,bar,target_long,opening_event,cash_after_open,shares_after_open,opening_fee,liquidation_fee,equity,cash,shares,peak,max_drawdown,notional,fees,trades\n";
        for (std::size_t s = 0; s < configs.size(); ++s)
            for (std::size_t i = 0; i < eligible; ++i) {
                const auto& r = traces[s * eligible + i];
                const auto& state = r.after_close;
                trace << s << ',' << spans.back() + i << ',' << r.target_long << ',' << r.opening_event << ','
                      << r.cash_after_open << ',' << r.shares_after_open << ',' << r.opening_fee << ','
                      << r.liquidation_fee << ',' << r.equity << ',' << state.cash << ',' << state.shares << ','
                      << state.peak << ',' << state.max_drawdown << ',' << state.notional << ','
                      << state.fees << ',' << state.trades << '\n';
            }
        trace.close();
    }
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0) throw std::runtime_error("getrusage failed");
#ifdef __APPLE__
    const auto rss = static_cast<std::uint64_t>(usage.ru_maxrss);
#else
    const auto rss = static_cast<std::uint64_t>(usage.ru_maxrss) * 1024;
#endif
    const auto matrix_bytes = features.size() * sizeof(double);
    std::cout << std::setprecision(17)
              << "{\"timed\":" << (timed ? "true" : "false")
              << ",\"order\":\"" << order_name << "\",\"layout\":\"" << layout_name
              << "\",\"bars\":" << bars.size() << ",\"windows\":" << spans.size()
              << ",\"configs\":" << configs.size() << ",\"eligible_bars\":" << eligible
              << ",\"capital\":" << rules.capital << ",\"fee\":" << rules.fee
              << ",\"feature_ns\":" << ns(start, prepared) << ",\"layout_ns\":" << ns(prepared, laid_out)
              << ",\"setup_ns\":" << ns(laid_out, set_up) << ",\"replay_ns\":" << ns(set_up, replayed)
              << ",\"summary_ns\":" << ns(replayed, finished) << ",\"prepared_ns\":" << ns(set_up, finished)
              << ",\"whole_ns\":" << ns(start, finished)
              << ",\"feature_bytes\":" << matrix_bytes
              << ",\"conversion_scratch_bytes\":" << (layout == strategy::Layout::snapshot ? matrix_bytes : 0)
              << ",\"bars_bytes\":" << bars.size() * sizeof(Bar)
              << ",\"config_bytes\":" << configs.size() * sizeof(strategy::Config)
              << ",\"state_bytes\":" << states.size() * sizeof(strategy::State)
              << ",\"summary_bytes\":" << summaries.size() * sizeof(strategy::Summary)
              << ",\"peak_rss_bytes\":" << rss << "}\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << "strategy_replay: " << error.what() << '\n';
    return 2;
}
