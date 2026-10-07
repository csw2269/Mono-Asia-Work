cmake_minimum_required(VERSION 3.20)
project(pluto_source_recovery_p1b LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(pluto_p1b STATIC
    src/proc_client.cpp
    src/deferred_turn_buffer.cpp
    src/action_slice.cpp
    src/lifecycle.cpp
)
target_include_directories(pluto_p1b PUBLIC include)

if(WIN32)
    target_compile_definitions(pluto_p1b PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
    target_link_libraries(pluto_p1b PRIVATE winmm)
endif()

add_executable(test_protocol tests/test_protocol.cpp)
target_link_libraries(test_protocol PRIVATE pluto_p1b)

enable_testing()
add_test(NAME protocol_and_vertical_slice COMMAND test_protocol)
