cmake_minimum_required(VERSION 3.4)
project(cmake_wrapper)

include("conanbuildinfo.cmake")
conan_basic_setup()
set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)

add_subdirectory("source_subfolder")

set_target_properties(parg PROPERTIES PUBLIC_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/source_subfolder/parg.h")

install(TARGETS parg)
