include(CheckCXXSourceCompiles)
check_cxx_source_compiles("
#include <experimental/simd>
int main() {
  std::experimental::native_simd<double> x(1.0);
  return x.size() >= 2 ? 0 : 1;
}" OIR_HAS_EXPERIMENTAL_SIMD)
if(NOT OIR_HAS_EXPERIMENTAL_SIMD)
    message(FATAL_ERROR "Use a toolchain with <experimental/simd>, e.g. the barrier-debug preset")
endif()

add_library(barrier_core SHARED src/barrier.cpp src/api.cpp)
target_include_directories(barrier_core PUBLIC src)
target_link_libraries(barrier_core PUBLIC measured_options)
target_compile_options(barrier_core PUBLIC -fno-fast-math -ffp-contract=off)
set_target_properties(barrier_core PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

add_executable(barrier_bench src/benchmark.cpp)
target_link_libraries(barrier_bench PRIVATE barrier_core)
set_target_properties(barrier_bench PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

if(BUILD_TESTING)
    add_executable(barrier_tests tests/barrier_tests.cpp)
    target_link_libraries(barrier_tests PRIVATE barrier_core)
    add_test(NAME barrier_correctness COMMAND barrier_tests)

    if(EXISTS "${PROJECT_SOURCE_DIR}/.venv/bin/python" AND NOT DEFINED Python3_EXECUTABLE)
        set(Python3_EXECUTABLE "${PROJECT_SOURCE_DIR}/.venv/bin/python")
    endif()
    find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
    add_test(NAME barrier_analysis
        COMMAND "${Python3_EXECUTABLE}" -m unittest discover
        -s "${CMAKE_CURRENT_SOURCE_DIR}/tests" -p "test_*.py" -v)
    set_tests_properties(barrier_analysis PROPERTIES
        ENVIRONMENT "MPLCONFIGDIR=${CMAKE_BINARY_DIR}/matplotlib;XDG_CACHE_HOME=${CMAKE_BINARY_DIR}/cache")
endif()

if(OIR_BARRIER_PRECISION)
    add_subdirectory(precision)
endif()
