#ifndef NESTED_MACROS_HEADER_HPP
#define NESTED_MACROS_HEADER_HPP

// Define base configuration macros
#define CONFIG_LEVEL_1 1
#define CONFIG_LEVEL_2 2
#define CONFIG_LEVEL_3 3

#ifndef BUILD_CONFIG
#define BUILD_CONFIG 2
#endif

// First level of nesting - build configuration
#if BUILD_CONFIG == 1
    #define BASIC_FEATURES
    #ifdef BASIC_FEATURES
        #include "basic_feature.hpp"
        #ifdef ENABLE_LOGGING
            #if defined(LOG_LEVEL) && LOG_LEVEL >= 1
                #include "basic_logging.hpp"
                #ifdef DEBUG_MODE
                    #if DEBUG_MODE > 0
                        #include "debug_basic.hpp"
                    #endif
                #endif
            #endif
        #endif
    #endif

#elif BUILD_CONFIG == 2
    #define ADVANCED_FEATURES
    #define BASIC_FEATURES
    
    #ifdef BASIC_FEATURES
        #include "basic_feature.hpp"
        // #include "red_herring_cpp_style.hpp"  
        /* #include "red_herring_c_style.hpp" */
    #endif
    
    #ifdef ADVANCED_FEATURES
        #include "advanced_feature.hpp"
        
        // Nested platform-specific logic
        #ifdef __linux__
            #define LINUX_ADVANCED
            #ifdef LINUX_ADVANCED
                #include "linux_advanced.hpp"
                #if defined(USE_EPOLL) && USE_EPOLL != 0
                    #ifdef ENABLE_THREADING
                        #if defined(THREAD_COUNT) && THREAD_COUNT > 1
                            #include "linux_epoll_threading.hpp"
                            #ifdef NUMA_SUPPORT
                                #if NUMA_SUPPORT == 1
                                    #include "numa_threading.hpp"
                                #endif
                            #endif
                        #endif
                    #endif
                #endif
            #endif
            
        #elif defined(_WIN32)
            #define WINDOWS_ADVANCED
            #ifdef WINDOWS_ADVANCED
                #include "windows_advanced.hpp"
                #ifdef USE_IOCP
                    #if USE_IOCP > 0
                        #include "windows_iocp.hpp"
                        #ifdef ENABLE_THREADING
                            #if defined(THREAD_COUNT) && THREAD_COUNT > 1
                                #include "windows_iocp_threading.hpp"
                            #endif
                        #endif
                    #endif
                #endif
            #endif
        #endif
        
        // Complex feature interdependencies
        #ifdef ENABLE_NETWORKING
            #if ENABLE_NETWORKING == 1
                #include "networking_base.hpp"
                #ifdef ENABLE_SSL
                    #if defined(SSL_VERSION) && SSL_VERSION >= 3
                        #include "ssl_networking.hpp"
                        #ifdef ENABLE_CERTIFICATES
                            #if ENABLE_CERTIFICATES != 0
                                #include "certificate_validation.hpp"
                                #ifdef STRICT_VALIDATION
                                    #if STRICT_VALIDATION == 1
                                        #include "strict_cert_validation.hpp"
                                    #endif
                                #endif
                            #endif
                        #endif
                    #endif
                #endif
            #endif
        #endif
    #endif

#elif BUILD_CONFIG == 3
    #define EXPERT_FEATURES
    #define ADVANCED_FEATURES  
    #define BASIC_FEATURES
    
    #ifdef BASIC_FEATURES
        #include "basic_feature.hpp"
    #endif
    
    #ifdef ADVANCED_FEATURES
        #include "advanced_feature.hpp"
    #endif
    
    #ifdef EXPERT_FEATURES
        #include "expert_feature.hpp"
        
        // Deeply nested expert configuration
        #ifdef ENABLE_EXPERT_MODE
            #if ENABLE_EXPERT_MODE == 1
                #include "expert_mode_base.hpp"
                
                #ifdef CUSTOM_ALLOCATOR
                    #if defined(ALLOCATOR_TYPE) && ALLOCATOR_TYPE == 2
                        #include "custom_allocator.hpp"
                        #ifdef MEMORY_TRACKING
                            #if MEMORY_TRACKING > 0
                                #include "memory_tracker.hpp"
                                #ifdef LEAK_DETECTION
                                    #if LEAK_DETECTION == 1
                                        #include "leak_detector.hpp"
                                        #ifdef STACK_TRACE
                                            #if STACK_TRACE != 0
                                                #include "stack_tracer.hpp"
                                            #endif
                                        #endif
                                    #endif
                                #endif
                            #endif
                        #endif
                    #endif
                #endif
                
                // Complex optimization flags
                #ifdef OPTIMIZATION_LEVEL
                    #if OPTIMIZATION_LEVEL >= 3
                        #include "high_optimization.hpp"
                        #ifdef ENABLE_VECTORIZATION
                            #if defined(SIMD_SUPPORT) && SIMD_SUPPORT == 1
                                #include "simd_optimization.hpp"
                                #ifdef AVX_SUPPORT
                                    #if AVX_SUPPORT >= 2
                                        #include "avx2_optimization.hpp"
                                        #ifdef ENABLE_FMA
                                            #if ENABLE_FMA == 1
                                                #include "fma_optimization.hpp"
                                            #endif
                                        #endif
                                    #endif
                                #endif
                            #endif
                        #endif
                    #endif
                #endif
            #endif
        #endif
    #endif

#else
    #error "Unknown BUILD_CONFIG value"
#endif

// Additional complex macro logic with interdependent conditions
#ifdef ENABLE_PROFILING
    #if ENABLE_PROFILING == 1
        #include "profiling_base.hpp"
        #ifdef DETAILED_PROFILING
            #if defined(PROFILING_LEVEL) && PROFILING_LEVEL > 2
                #include "detailed_profiler.hpp"
                #ifdef MEMORY_PROFILING
                    #if MEMORY_PROFILING != 0
                        #include "memory_profiler.hpp"
                        #ifdef CPU_PROFILING
                            #if defined(CPU_PROFILING) && CPU_PROFILING == 1
                                #include "cpu_profiler.hpp"
                                #ifdef CACHE_PROFILING
                                    #if CACHE_PROFILING > 0
                                        #include "cache_profiler.hpp"
                                    #endif
                                #endif
                            #endif
                        #endif
                    #endif
                #endif
            #endif
        #endif
    #endif
#endif

#endif // NESTED_MACROS_HEADER_HPP