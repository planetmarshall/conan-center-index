cmake_minimum_required(VERSION 3.1.3)
project(CopperspiceTestPackage)

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(TARGETS)

add_executable(copperspice_test_package main.cpp)
target_compile_features(copperspice_test_package PRIVATE cxx_std_17)
target_link_libraries(copperspice_test_package PRIVATE ${CONAN_TARGETS})

