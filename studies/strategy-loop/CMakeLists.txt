add_executable(strategy_layout_example examples/layout.cpp)
target_compile_features(strategy_layout_example PRIVATE cxx_std_23)
target_link_libraries(strategy_layout_example PRIVATE measured_options)
set_target_properties(strategy_layout_example PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
if(BUILD_TESTING)
    add_test(NAME strategy_layout_example COMMAND strategy_layout_example)
endif()

add_library(strategy_core STATIC src/replay.cpp)
target_include_directories(strategy_core PUBLIC src)
target_compile_features(strategy_core PUBLIC cxx_std_23)
target_link_libraries(strategy_core PUBLIC measured_options)
target_compile_options(strategy_core PUBLIC -fno-fast-math -ffp-contract=off)
add_executable(strategy_replay src/main.cpp)
target_link_libraries(strategy_replay PRIVATE strategy_core)
set_target_properties(strategy_replay PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

if(BUILD_TESTING)
    if(EXISTS "${PROJECT_SOURCE_DIR}/.venv/bin/python" AND NOT DEFINED Python3_EXECUTABLE)
        set(Python3_EXECUTABLE "${PROJECT_SOURCE_DIR}/.venv/bin/python")
    endif()
    find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
    add_test(NAME strategy_accounting
        COMMAND "${Python3_EXECUTABLE}" -m unittest discover
        -s "${CMAKE_CURRENT_SOURCE_DIR}/tests" -p "test_*.py" -v)
    set_tests_properties(strategy_accounting PROPERTIES
        ENVIRONMENT "STRATEGY_BINARY=$<TARGET_FILE:strategy_replay>")
endif()
