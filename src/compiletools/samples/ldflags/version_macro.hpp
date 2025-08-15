#ifndef VERSION_MACRO_HPP
#define VERSION_MACRO_HPP

// Define version macros for conditional linking
#define API_VERSION_MAJOR 2
#define API_VERSION_MINOR 1
#define API_VERSION_PATCH 0

// Combined version for easy comparison: MAJOR * 10000 + MINOR * 100 + PATCH
#define API_VERSION ((API_VERSION_MAJOR * 10000) + (API_VERSION_MINOR * 100) + API_VERSION_PATCH)

#endif // VERSION_MACRO_HPP