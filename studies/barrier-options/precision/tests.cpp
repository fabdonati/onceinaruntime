#include "precision.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>

namespace fp = barrier::precision;
void require(bool ok,const char* message) { if (!ok) throw std::runtime_error(message); }
template<class F> void rejects(F f) {
    bool caught = false; try { f(); } catch (const std::exception&) { caught = true; }
    require(caught,"expected float rejection");
}
void compare(const std::vector<float>& factors,std::size_t n,std::size_t steps,const fp::Contract& c,
             const std::vector<float>* literal=nullptr) {
    const fp::Input source{factors,n,steps}; fp::validate(source,c);
    std::vector<float> reference(n),out(n),instrumented(n),transposed(factors.size());
    barrier::Diagnostics ref;
    const auto price = fp::diagnose(source,c,barrier::Method::scalar,reference,ref);
    if (literal) require(reference == *literal,"float literal payoff mismatch");
    for (std::size_t p=0;p<n;++p) for (std::size_t t=0;t<steps;++t) transposed[t*n+p]=factors[p*steps+t];
    for (const auto layout : {barrier::Layout::path_major,barrier::Layout::step_major}) {
        const fp::Input in{layout == barrier::Layout::path_major ? factors : transposed,n,steps,layout};
        fp::validate(in,c);
        for (const auto method : {barrier::Method::scalar,barrier::Method::fixed,barrier::Method::refill}) {
            std::fill(out.begin(),out.end(),std::numeric_limits<float>::quiet_NaN());
            require(fp::evaluate(in,c,method,out) == price && out == reference,"ordered float payoff or aggregate mismatch");
            barrier::Diagnostics d;
            require(fp::diagnose(in,c,method,instrumented,d) == price && instrumented == reference,"float diagnostic mismatch");
            require(d.lifetimes == ref.lifetimes && d.knocked_out == ref.knocked_out,"float path identity mismatch");
            require(d.useful_lane_steps == std::accumulate(d.lifetimes.begin(),d.lifetimes.end(),std::uint64_t(0)),"float work count");
            require(d.available_lane_steps >= d.useful_lane_steps,"float occupancy bound");
            const auto replacements = method == barrier::Method::refill && c.spot < c.barrier && n > fp::native_width() ? n-fp::native_width() : 0;
            require(d.replacements == replacements,"float refill count");
        }
    }
}
int main() {
    try {
        const std::vector<float> fixture{2,.5f,1, 1,1,2, 1,1,1, .5f,1,1, 1.25f,1,1, 1,2.5f,.5f, 1,1.5f,1};
        const std::vector<float> expected{0,0,1,0,2,0,3};
        compare(fixture,7,3,{8,6,16,.5f},&expected);
        const std::vector<float> zero(7,0);
        compare(fixture,7,3,{8,6,8,.5f},&zero);
        barrier::Diagnostics literal;
        std::vector<float> out(7);
        fp::diagnose({fixture,7,3},{8,6,16,.5f},barrier::Method::refill,out,literal);
        require(literal.lifetimes == std::vector<std::uint64_t>({1,3,3,3,3,2,3}),"float literal dates");
        require(literal.knocked_out == std::vector<std::uint8_t>({1,1,0,0,0,1,0}),"float literal knockouts");
        const auto w = fp::native_width();
        std::mt19937 rng(99173); std::uniform_real_distribution<float> draw(.85f,1.15f);
        for (const auto n : {std::size_t(0),std::size_t(1),w-1,w,w+1,2*w-1,3*w+1,std::size_t(257)})
            for (const auto steps : {std::size_t(1),std::size_t(2),std::size_t(17),std::size_t(252)}) {
                std::vector<float> values(n*steps); for (auto& value : values) value=draw(rng);
                for (const auto b : {99.f,100.f,105.f,120.f,150.f,std::numeric_limits<float>::infinity()})
                    compare(values,n,steps,{100,100,b,static_cast<float>(std::exp(-.02))});
            }
        // Input rounding can change a barrier decision; it must not be hidden by aggregate tolerance.
        const std::vector<double> near{1.5-std::ldexp(1.0,-25),1.0};
        const std::vector<float> rounded(near.begin(),near.end());
        std::vector<double> double_out(1); std::vector<float> float_out(1);
        barrier::Diagnostics double_d,float_d;
        barrier::diagnose({near,1,2},{8,6,12,1},barrier::Method::scalar,double_out,double_d);
        fp::diagnose({rounded,1,2},{8,6,12,1},barrier::Method::refill,float_out,float_d);
        require(double_d.knocked_out[0] == 0 && float_d.knocked_out[0] == 1 && double_out[0] > 0 && float_out[0] == 0,"near-barrier precision counterexample");
        const std::vector<float> one{1};
        for (const auto bad : {0.f,-1.f,std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()}) {
            rejects([&]{const std::vector<float> x{bad};fp::validate({x,1,1},{8,6,16,1});});
            rejects([&]{fp::validate({one,1,1},{bad,6,16,1});});
            rejects([&]{fp::validate({one,1,1},{8,6,16,bad});});
        }
        rejects([&]{fp::validate({one,1,0},{8,6,16,1});});
        rejects([&]{fp::validate({one,2,1},{8,6,16,1});});
        rejects([&]{fp::validate({one,std::numeric_limits<std::size_t>::max(),2},{8,6,16,1});});
        rejects([&]{fp::validate({one,1,1,static_cast<barrier::Layout>(99)},{8,6,16,1});});
        rejects([&]{const std::vector<float> x{std::numeric_limits<float>::max()};fp::validate({x,1,1},{8,6,16,1});});
        rejects([&]{const std::vector<float> x{std::numeric_limits<float>::denorm_min()};fp::validate({x,1,1},{.01f,0,1,1});});
        rejects([&]{fp::validate({one,1,1},{8,0,16,std::numeric_limits<float>::max()});});
        rejects([&]{std::vector<float> empty;fp::evaluate({one,1,1},{8,6,16,1},barrier::Method::scalar,empty);});
        rejects([&]{fp::evaluate({one,1,1},{8,6,16,1},static_cast<barrier::Method>(99),float_out);});
        std::cout<<"Float literal/tail/layout/refill/range checks and precision counterexample passed; float lanes="<<w<<", double lanes="<<barrier::native_width()<<'\n';
    } catch (const std::exception& error) { std::cerr<<error.what()<<'\n'; return 1; }
}
