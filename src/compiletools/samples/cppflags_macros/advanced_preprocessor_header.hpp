#ifndef ADVANCED_PREPROCESSOR_HEADER_HPP
#define ADVANCED_PREPROCESSOR_HEADER_HPP

// Test #if expressions with numeric comparisons
#define VERSION 3
#if VERSION >= 2
#include "version_ge_2_feature.hpp"
#endif

// Test complex #if defined expressions
#if defined(FEATURE_A) && defined(FEATURE_B)
#include "combined_features.hpp"
#elif defined(FEATURE_A) || defined(FEATURE_C)
#include "partial_features.hpp"
#endif

// Test #undef functionality
#define TEMP_MACRO 1
#ifdef TEMP_MACRO
#include "temp_defined.hpp"
#endif
#undef TEMP_MACRO
#ifdef TEMP_MACRO
#include "temp_still_defined.hpp"  // Should NOT be included
#endif

// Test alternative forms
#if defined(ALT_FORM_TEST)
#include "alt_form_feature.hpp"
#endif

// Test complex numeric expressions
#define MAJOR_VER 2
#define MINOR_VER 5
#if (MAJOR_VER * 100 + MINOR_VER) >= 205
#include "version_205_plus.hpp"
#endif

#endif