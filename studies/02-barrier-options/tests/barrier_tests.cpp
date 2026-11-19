#include "barrier.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>

using namespace barrier;
void require(bool ok, const char* what) { if (!ok) throw std::runtime_error(what); }
template<class F> void rejects(F f) {
    bool threw=false;
    try { f(); } catch (const std::exception&) { threw=true; }
    require(threw,"invalid input accepted");
}
std::vector<double> transpose(const std::vector<double>& a, std::size_t n, std::size_t t) {
    std::vector<double> b(a.size());
    for (std::size_t p=0;p<n;++p) for (std::size_t s=0;s<t;++s) b[s*n+p]=a[p*t+s];
    return b;
}
void compare(const std::vector<double>& factors, std::size_t n, std::size_t t, const Contract& c,
             const std::vector<double>* literal=nullptr,
             const std::vector<std::uint64_t>* stops=nullptr,
             const std::vector<std::uint8_t>* knocked=nullptr) {
    const Input original{factors,n,t,Layout::path_major};
    validate(original,c);
    std::vector<double> ref(n), out(n), instrumented(n);
    Diagnostics reference;
    const auto price=diagnose(original,c,Method::scalar,ref,reference);
    if (literal) require(ref == *literal,"literal payoff fixture");
    if (stops) require(reference.lifetimes == *stops,"literal stopping dates");
    if (knocked) require(reference.knocked_out == *knocked,"literal knockout fixture");
    auto transposed=transpose(factors,n,t);
    for (const auto l : {Layout::path_major,Layout::step_major}) {
        const Input in{l==Layout::path_major ? factors : transposed,n,t,l};
        validate(in,c);
        for (const auto m : {Method::scalar,Method::fixed,Method::refill}) {
            std::fill(out.begin(),out.end(),std::numeric_limits<double>::quiet_NaN());
            require(evaluate(in,c,m,out)==price,"aggregate disagreement");
            require(out==ref,"ordered payoff disagreement or unwritten path");
            Diagnostics d;
            require(diagnose(in,c,m,instrumented,d)==price && instrumented==ref,"instrumented disagreement");
            require(d.lifetimes==reference.lifetimes && d.knocked_out==reference.knocked_out,"path/date identity");
            require(d.useful_lane_steps==std::accumulate(d.lifetimes.begin(),d.lifetimes.end(),std::uint64_t(0)),"useful work");
            require(d.available_lane_steps>=d.useful_lane_steps,"occupancy bounds");
            const auto expected = m==Method::refill && c.spot<c.barrier && n>native_width() ? n-native_width() : 0;
            require(d.replacements==expected,"replacement count");
        }
    }
}
int main() {
    try {
        // Powers of two ensure exact literal arithmetic, including barrier equality.
        const std::vector<double> fixture{
            2, .5, 1, // first-date equality, then falls: remains dead
            1, 1, 2, // last-date equality
            1, 1, 1, // positive survivor
            .5, 1, 1, // OTM survivor
            1.25, 1, 1, // distinct positive payoff
            1, 2.5, .5, // overshoot, then fall
            1, 1.5, 1};
        const Contract c{8,6,16,.5};
        const std::vector<double> expected{0,0,1,0,2,0,3};
        const std::vector<std::uint64_t> stops{1,3,3,3,3,2,3};
        const std::vector<std::uint8_t> knocked{1,1,0,0,0,1,0};
        compare(fixture,7,3,c,&expected,&stops,&knocked);
        auto initial=c; initial.barrier=8;
        const std::vector<double> zero(7,0);
        const std::vector<std::uint64_t> zero_stops(7,0);
        const std::vector<std::uint8_t> all_hit(7,1);
        compare(fixture,7,3,initial,&zero,&zero_stops,&all_hit);

        const auto w=native_width();
        std::mt19937_64 rng(71829);
        std::uniform_real_distribution<double> factor(.85,1.15);
        for (const auto n : {std::size_t(0),std::size_t(1),w-1,w,w+1,3*w+1,std::size_t(257)}) {
            for (const auto t : {std::size_t(1),std::size_t(2),std::size_t(17),std::size_t(252)}) {
                std::vector<double> a(n*t);
                for (auto& x:a) x=factor(rng);
                for (const auto b:{99.,100.,105.,120.,150.,std::numeric_limits<double>::infinity()})
                    compare(a,n,t,{100,100,b,std::exp(-.02)});
                std::vector<double> previous(n,0), out(n);
                const Input in{a,n,t};
                for (const auto b:{105.,120.,150.,std::numeric_limits<double>::infinity()}) {
                    evaluate(in,{100,100,b,1},Method::refill,out);
                    for (std::size_t p=0;p<n;++p) require(out[p]>=previous[p],"pathwise barrier monotonicity");
                    previous=out;
                }
            }
        }
        // A disabled barrier is a direct vanilla payoff; no barrier formula involved.
        std::vector<double> vanilla_expected(7);
        for (std::size_t p=0;p<7;++p) {
            double spot=8;
            for (std::size_t t=0;t<3;++t) spot*=fixture[p*3+t];
            vanilla_expected[p]=.5*std::max(spot-6,0.);
        }
        compare(fixture,7,3,{8,6,std::numeric_limits<double>::infinity(),.5},&vanilla_expected);
        // Sigma=0 gives identical deterministic paths at every lane and boundary.
        std::vector<double> deterministic(11*252,std::exp(.02/252));
        compare(deterministic,11,252,{100,100,120,std::exp(-.02)});

        const std::vector<double> one{1};
        for (const auto bad:{0.,-1.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}) {
            rejects([&]{const std::vector<double> a{bad}; validate({a,1,1},c);});
            rejects([&]{auto x=c;x.spot=bad;validate({one,1,1},x);});
            rejects([&]{auto x=c;x.discount=bad;validate({one,1,1},x);});
        }
        for (const auto bad:{0.,-1.,std::numeric_limits<double>::quiet_NaN()})
            rejects([&]{auto x=c;x.barrier=bad;validate({one,1,1},x);});
        for (const auto bad:{-1.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()})
            rejects([&]{auto x=c;x.strike=bad;validate({one,1,1},x);});
        rejects([&]{validate({one,1,0},c);});
        rejects([&]{validate({one,2,1},c);});
        rejects([&]{validate({one,std::numeric_limits<std::size_t>::max(),2},c);});
        rejects([&]{const std::vector<double> a{std::numeric_limits<double>::max()};validate({a,1,1},c);});
        rejects([&]{const std::vector<double> a{std::numeric_limits<double>::denorm_min()};validate({a,1,1},{.01,0,1,1});});
        rejects([&]{const std::vector<double> a{1};validate({a,1,1},{8,0,16,std::numeric_limits<double>::max()});});
        rejects([&]{std::vector<double> out;evaluate({one,1,1},c,Method::scalar,out);});
        std::cout<<"Literal payoffs/dates, refill identity, tails, both layouts, finite range, vanilla, monotonicity and deterministic checks passed; native width="<<w<<'\n';
    } catch (const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
