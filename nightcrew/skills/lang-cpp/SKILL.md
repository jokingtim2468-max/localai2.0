---
name: lang-cpp
description: C and C++ apps with CMake
domain: cpp
triggers: [c++, cpp, cmake, clang, gcc, msvc, header]
---
- Configure + build: `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release` then `cmake --build build -j`.
- Minimal CMakeLists: `cmake_minimum_required(VERSION 3.20) project(App CXX) set(CMAKE_CXX_STANDARD 20) add_executable(app src/main.cpp)`.
- GUI: Dear ImGui (+ GLFW) for tools, Qt6 for full apps.
- Traps: RAII over new/delete, std::unique_ptr, build with -Wall -Wextra; read the FIRST compiler error.
