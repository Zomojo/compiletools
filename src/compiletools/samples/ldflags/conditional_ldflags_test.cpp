#include <iostream>

#ifndef USE_PRODUCTION_LIBS
//#LDFLAGS=-ldebug_library -ltest_framework
#else  
//#LDFLAGS=-lproduction_library -loptimized_framework
#endif

int main() {
#ifndef USE_PRODUCTION_LIBS
    std::cout << "Debug build - using debug libraries" << std::endl;
#else
    std::cout << "Production build - using production libraries" << std::endl;
#endif
    return 0;
}