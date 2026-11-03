cmake_minimum_required(VERSION 3.21)
project(once_in_a_runtime VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
option(MEASURED_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)

add_library(measured_options INTERFACE)
target_compile_options(measured_options INTERFACE
    $<$<CXX_COMPILER_ID:Clang,AppleClang,GNU>:-Wall;-Wextra;-Wpedantic;-Wconversion;-Wshadow>
    $<$<CXX_COMPILER_ID:MSVC>:/W4;/permissive->)
if(MEASURED_SANITIZERS)
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        message(FATAL_ERROR "The sanitizer preset requires Clang or GCC")
    endif()
    target_compile_options(measured_options INTERFACE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(measured_options INTERFACE -fsanitize=address,undefined)
endif()

include(CTest)
add_executable(toolchain_check tools/toolchain_check.cpp)
target_link_libraries(toolchain_check PRIVATE measured_options)
add_subdirectory(experiments/001-message-replay)
