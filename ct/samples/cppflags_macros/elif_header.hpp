#ifndef ELIF_HEADER_HPP
#define ELIF_HEADER_HPP

#ifdef VERSION_1
#include "version1_feature.hpp"
#elif defined(VERSION_2)
#include "version2_feature.hpp"
#elif defined(VERSION_3)
#include "version3_feature.hpp"
#else
#include "default_feature.hpp"
#endif

#endif