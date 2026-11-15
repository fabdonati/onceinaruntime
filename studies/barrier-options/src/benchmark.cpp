#include "barrier.hpp"
#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using Clock = std::chrono::steady_clock;
using namespace barrier;
template<class T> void write(const std::string& path, const std::vector<T>& x) {
    std::ofstream f(path, std::ios::binary);
    if (!f.write(reinterpret_cast<const char*>(x.data()), static_cast<std::streamsize>(x.size() * sizeof(T))))
        throw std::runtime_error("cannot write " + path);
}
std::size_t count(const char* text) {
    const std::string s(text);
    if (s.empty() || s.find_first_not_of("0123456789") != std::string::npos)
        throw std::invalid_argument("expected nonnegative integer");
    std::size_t used = 0;
    const auto n = std::stoull(s, &used);
    if (used != s.size() || n > std::numeric_limits<std::size_t>::max()) throw std::invalid_argument("count overflow");
    return static_cast<std::size_t>(n);
}
int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--timer") {
            std::cout << "{\"steady\":" << (Clock::is_steady ? "true" : "false") << ",\"deltas_ns\":[";
            // Collect first; formatting must not contaminate successive clock reads.
            std::vector<long long> deltas(10000);
            auto previous = Clock::now();
            for (auto& delta : deltas) { const auto now = Clock::now(); delta = std::chrono::duration_cast<std::chrono::nanoseconds>(now-previous).count(); previous=now; }
            for (std::size_t i=0;i<deltas.size();++i) std::cout << (i ? "," : "") << deltas[i];
            std::cout << "]}\n"; return 0;
        }
        if (argc != 9 && argc != 10) throw std::invalid_argument("usage: barrier_bench factors.f64 paths steps path|step scalar|fixed|refill barrier discount output-prefix [--time]");
        if constexpr (std::endian::native != std::endian::little) throw std::runtime_error("input format is little endian");
        const auto n = count(argv[2]), t = count(argv[3]);
        if (!t || n > std::numeric_limits<std::size_t>::max() / t / sizeof(double)) throw std::invalid_argument("dimensions overflow");
        const std::string layout(argv[4]), method(argv[5]);
        if (layout != "path" && layout != "step") throw std::invalid_argument("bad layout");
        if (method != "scalar" && method != "fixed" && method != "refill") throw std::invalid_argument("bad method");
        const auto m = method == "scalar" ? Method::scalar : method == "fixed" ? Method::fixed : Method::refill;
        std::size_t used_b=0, used_d=0;
        const Contract c{100,100,std::stod(argv[6],&used_b),std::stod(argv[7],&used_d)};
        if (used_b != std::string(argv[6]).size() || used_d != std::string(argv[7]).size()) throw std::invalid_argument("bad numeric contract");
        const std::string prefix(argv[8]);
        const bool timed = argc == 10;
        if (timed && std::string(argv[9]) != "--time") throw std::invalid_argument("bad timing flag");
        std::vector<double> factors(n*t);
        std::ifstream file(argv[1], std::ios::binary);
        if (!file.read(reinterpret_cast<char*>(factors.data()), static_cast<std::streamsize>(factors.size()*sizeof(double))) || file.peek() != std::char_traits<char>::eof())
            throw std::invalid_argument("input byte count differs from dimensions");
        const Input in{factors,n,t,layout == "path" ? Layout::path_major : Layout::step_major};
        validate(in,c);
        std::vector<double> out(n), reference(n), diag_out(n);
        const auto expected = evaluate(in,c,Method::scalar,reference);
        // One complete warm-up of the selected method before a single observation.
        const auto warm = evaluate(in,c,m,out);
        if (out != reference || warm != expected) throw std::runtime_error("warm-up pathwise mismatch");
        long long ns = 0;
        double price = warm;
        if (timed) {
            const auto begin = Clock::now();
            price = evaluate(in,c,m,out);
            ns = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-begin).count();
        }
        if (out != reference || price != expected) throw std::runtime_error("pathwise mismatch");
        Diagnostics d;
        if (diagnose(in,c,m,diag_out,d) != price || diag_out != out) throw std::runtime_error("diagnostic mismatch");
        write(prefix+".payoffs.f64",out);
        write(prefix+".lifetimes.u64",d.lifetimes);
        write(prefix+".knocked.u8",d.knocked_out);
        std::cout << std::setprecision(17) << "{\"paths\":"<<n<<",\"steps\":"<<t<<",\"layout\":\""<<layout
          <<"\",\"method\":\""<<method<<"\",\"barrier\":";
        if (std::isfinite(c.barrier)) std::cout<<c.barrier; else std::cout<<"null";
        std::cout<<",\"discount\":"<<c.discount<<",\"native_width\":"<<native_width()<<",\"price\":"<<price
          <<",\"timed\":"<<(timed?"true":"false")<<",\"prepared_ns\":"<<ns
          <<",\"useful_lane_steps\":"<<d.useful_lane_steps<<",\"available_lane_steps\":"<<d.available_lane_steps
          <<",\"replacements\":"<<d.replacements<<",\"validated_cpp\":true}\n";
    } catch (const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
