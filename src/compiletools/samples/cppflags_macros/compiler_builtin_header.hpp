#ifndef COMPILER_BUILTIN_HEADER_HPP
#define COMPILER_BUILTIN_HEADER_HPP

#ifdef __GNUC__
#include "gcc_feature.hpp"
#endif

#ifdef __clang__
#include "clang_feature.hpp"
#endif

#ifdef __TINYC__
#include "tcc_feature.hpp"
#endif

#ifdef _MSC_VER
#include "msvc_feature.hpp"
#endif

#ifdef __INTEL_COMPILER
#include "intel_feature.hpp"
#endif

#ifdef __EMSCRIPTEN__
#include "emscripten_feature.hpp"
#endif

#ifdef __ARMCC_VERSION
#include "armcc_feature.hpp"
#endif

#ifdef __x86_64__
#include "x86_64_feature.hpp"
#endif

#ifdef __arm__
#include "arm_feature.hpp"
#endif

#ifdef __aarch64__
#include "aarch64_feature.hpp"
#endif

#ifdef __linux__
#include "linux_feature.hpp"
#endif

#ifdef __riscv
#include "riscv_feature.hpp"
#endif

#endif