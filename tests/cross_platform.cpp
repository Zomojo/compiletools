#include "cross_platform.hpp"

#ifdef __linux__
//#SOURCE=cross_platform_lin.cpp
#else
//#SOURCE=cross_platform_win.cpp
#endif

// Put the generic parts that work independent of platform here
// and put the platform specific parts into cross_platform_<win/lin>.cpp
std::string Cross_Platform::hello_world() const
{
    return "hello world";
}

