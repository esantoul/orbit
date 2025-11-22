cmake_minimum_required(VERSION 3.15)
project(cmake_wrapper)

set(CMAKE_CXX_STANDARD 17)

# Conan 2.x: Dependencies are found via find_package()
find_package(protobuf REQUIRED CONFIG)
find_package(OpenSSL REQUIRED CONFIG)
find_package(c-ares REQUIRED CONFIG)
find_package(absl REQUIRED CONFIG)

# Set up protoc variables for gRPC
# In Conan 2.x, protoc is provided as a target by the protobuf package
get_target_property(_gRPC_PROTOBUF_PROTOC_EXECUTABLE protobuf::protoc LOCATION)
set(_gRPC_PROTOBUF_PROTOC_LIBRARIES protobuf::libprotoc)  # Compiler library
set(_gRPC_PROTOBUF_LIBRARIES protobuf::libprotobuf)  # Runtime library
get_target_property(_gRPC_PROTOBUF_WELLKNOWN_INCLUDE_DIR protobuf::libprotobuf INTERFACE_INCLUDE_DIRECTORIES)
list(GET _gRPC_PROTOBUF_WELLKNOWN_INCLUDE_DIR 0 _gRPC_PROTOBUF_WELLKNOWN_INCLUDE_DIR)

# Set up OpenSSL and c-ares for gRPC
set(gRPC_CARES_PROVIDER "none" CACHE STRING "" FORCE)
set(_gRPC_CARES_LIBRARIES "c-ares::cares")

add_subdirectory("source_subfolder")
