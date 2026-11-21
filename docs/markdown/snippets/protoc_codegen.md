## New `protoc` code generator in codegen module

The codegen module now has a `protoc` wrapper for generating protobuf.
This handles the fact that `protoc` outputs mirror the structure of
input files. It can optionally handle the generation of grpc services.
C++ language is supported.
