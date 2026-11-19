#include "precision.hpp"
#include <bit>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>

using Clock = std::chrono::steady_clock;
namespace fp = barrier::precision;
template<class T> void write(const std::string& path, const std::vector<T>& values) {
    std::ofstream f(path, std::ios::binary);
    if (!f.write(reinterpret_cast<const char*>(values.data()), static_cast<std::streamsize>(values.size()*sizeof(T))))
        throw std::runtime_error("cannot write " + path);
}
std::size_t count(const char* text) {
    const std::string s(text);
    if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos)
        throw std::invalid_argument("expected nonnegative count");
    const auto value = std::stoull(s);
    if (value > std::numeric_limits<std::size_t>::max()) throw std::invalid_argument("count overflow");
    return static_cast<std::size_t>(value);
}
double number(const char* text) {
    std::size_t used = 0;
    const auto result = std::stod(text, &used);
    if (used != std::string(text).size()) throw std::invalid_argument("bad contract number");
    return result;
}

template<class T> int run(int argc, char** argv) {
    using Input = std::conditional_t<std::is_same_v<T,float>, fp::Input, barrier::Input>;
    using Contract = std::conditional_t<std::is_same_v<T,float>, fp::Contract, barrier::Contract>;
    const auto n = count(argv[3]), steps = count(argv[4]);
    if (!steps || n > std::numeric_limits<std::size_t>::max()/steps/sizeof(T) ||
        n*steps > static_cast<std::size_t>(std::numeric_limits<std::streamsize>::max())/sizeof(T))
        throw std::invalid_argument("input size overflow");
    const std::string layout(argv[5]), method(argv[6]), prefix(argv[9]);
    if (layout != "path" && layout != "step") throw std::invalid_argument("bad layout");
    if (method != "scalar" && method != "fixed" && method != "refill") throw std::invalid_argument("bad method");
    const auto m = method == "scalar" ? barrier::Method::scalar : method == "fixed" ? barrier::Method::fixed : barrier::Method::refill;
    const Contract contract{T(100),T(100),static_cast<T>(number(argv[7])),static_cast<T>(number(argv[8]))};
    const bool timed = argc == 11;
    if (timed && std::string(argv[10]) != "--time") throw std::invalid_argument("bad timing flag");
    std::vector<T> factors(n*steps);
    std::ifstream input(argv[2],std::ios::binary);
    if (!input.read(reinterpret_cast<char*>(factors.data()),static_cast<std::streamsize>(factors.size()*sizeof(T))) ||
        input.peek() != std::char_traits<char>::eof()) throw std::invalid_argument("input byte count mismatch");
    const Input in{factors,n,steps,layout == "path" ? barrier::Layout::path_major : barrier::Layout::step_major};
    validate(in,contract);
    std::vector<T> expected(n), output(n), instrumented(n);
    // Unqualified calls select the original double or separate float implementation.
    const auto reference = evaluate(in,contract,barrier::Method::scalar,expected);
    const auto warm = evaluate(in,contract,m,output);
    if (warm != reference || output != expected) throw std::runtime_error("warm-up mismatch");
    long long ns = 0;
    double price = warm;
    if (timed) {
        const auto start = Clock::now();
        price = evaluate(in,contract,m,output);
        ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count();
    }
    if (price != reference || output != expected) throw std::runtime_error("timed payoff mismatch");
    barrier::Diagnostics d;
    if (diagnose(in,contract,m,instrumented,d) != reference || instrumented != expected)
        throw std::runtime_error("instrumented payoff mismatch");
    const auto width = std::is_same_v<T,float> ? fp::native_width() : barrier::native_width();
    write(prefix+(std::is_same_v<T,float> ? ".payoffs.f32" : ".payoffs.f64"),output);
    write(prefix+".lifetimes.u64",d.lifetimes); write(prefix+".knocked.u8",d.knocked_out);
    std::cout << std::setprecision(17) << "{\"precision\":\""<<argv[1]<<"\",\"paths\":"<<n
      <<",\"steps\":"<<steps<<",\"layout\":\""<<layout<<"\",\"method\":\""<<method
      <<"\",\"barrier\":";
    if (std::isfinite(contract.barrier)) std::cout<<contract.barrier; else std::cout<<"null";
    std::cout<<",\"discount\":"<<contract.discount<<",\"native_width\":"<<width
      <<",\"input_bytes\":"<<factors.size()*sizeof(T)<<",\"output_bytes\":"<<output.size()*sizeof(T)
      <<",\"price\":"<<price<<",\"timed\":"<<(timed ? "true" : "false")<<",\"prepared_ns\":"<<ns
      <<",\"useful_lane_steps\":"<<d.useful_lane_steps<<",\"available_lane_steps\":"<<d.available_lane_steps
      <<",\"replacements\":"<<d.replacements<<",\"validated_cpp\":true,\"aggregation\":\"ordered FP64\"}\n";
    return 0;
}
int main(int argc,char** argv) {
    try {
        if constexpr (std::endian::native != std::endian::little) throw std::runtime_error("little-endian input required");
        if (argc == 2 && std::string(argv[1]) == "--info") {
            std::cout<<"{\"float_lanes\":"<<fp::native_width()<<",\"double_lanes\":"<<barrier::native_width()
                     <<",\"float_bytes\":"<<sizeof(float)<<",\"double_bytes\":"<<sizeof(double)
                     <<",\"steady_clock\":"<<(Clock::is_steady ? "true" : "false")<<"}\n";
            return 0;
        }
        if (argc != 10 && argc != 11)
            throw std::invalid_argument("usage: barrier_precision_bench f32|f64 factors paths steps path|step scalar|fixed|refill barrier discount output-prefix [--time]");
        if (std::string(argv[1]) == "f32") return run<float>(argc,argv);
        if (std::string(argv[1]) == "f64") return run<double>(argc,argv);
        throw std::invalid_argument("bad precision");
    } catch (const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
