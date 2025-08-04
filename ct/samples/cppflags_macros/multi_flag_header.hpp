#ifndef MULTI_FLAG_HEADER_HPP
#define MULTI_FLAG_HEADER_HPP

#ifdef FROM_CPPFLAGS
#include "cppflags_feature.hpp"
#endif

#ifdef FROM_CFLAGS
#include "cflags_feature.hpp" 
#endif

#ifdef FROM_CXXFLAGS
#include "cxxflags_feature.hpp"
#endif

#endif