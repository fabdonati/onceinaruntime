add_executable(strategy_layout_example examples/layout.cpp)
target_compile_features(strategy_layout_example PRIVATE cxx_std_23)
target_link_libraries(strategy_layout_example PRIVATE measured_options)
set_target_properties(strategy_layout_example PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
if(BUILD_TESTING)
    add_test(NAME strategy_layout_example COMMAND strategy_layout_example)
endif()
