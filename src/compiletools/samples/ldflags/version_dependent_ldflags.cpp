#include <iostream>
#include "version_macro.hpp"

// Conditional LDFLAGS based on API version defined in header file
// This exposes a bug: DirectMagicFlags can't evaluate complex #if expressions
#if API_VERSION >= 20100  // Version 2.1.0 or higher
//#LDFLAGS=-lnewapi -ladvanced_features
#else
//#LDFLAGS=-loldapi -lbasic_features
#endif

int main() {
    std::cout << "Using API version " << API_VERSION_MAJOR << "." 
              << API_VERSION_MINOR << "." << API_VERSION_PATCH << std::endl;
    
#if API_VERSION >= 20100
    std::cout << "Linked with new API and advanced features" << std::endl;
#else  
    std::cout << "Linked with old API and basic features" << std::endl;
#endif
    
    return 0;
}