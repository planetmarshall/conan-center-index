cmake_minimum_required(VERSION 3.15)

project(test_package CXX)

find_package(launchdarkly REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG)

add_executable(${PROJECT_NAME} main.cpp)
set_target_properties(${PROJECT_NAME} PROPERTIES POSITION_INDEPENDENT_CODE TRUE)
target_link_libraries(${PROJECT_NAME} PRIVATE launchdarkly::launchdarkly-cpp-client Boost::headers)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
