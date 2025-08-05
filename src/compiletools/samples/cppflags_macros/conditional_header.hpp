#ifndef CONDITIONAL_HEADER_HPP
#define CONDITIONAL_HEADER_HPP

// This should trigger an error if BUILD_MODE_TESTING is defined via -D flag
#ifdef BUILD_MODE_TESTING
#error "BUILD_MODE_TESTING should not be enabled in release builds"
#endif

// This should conditionally include a feature if ENABLE_ADVANCED_FEATURES is defined via -D flag
#ifdef ENABLE_ADVANCED_FEATURES
#include "advanced_feature.hpp"
#endif

#endif