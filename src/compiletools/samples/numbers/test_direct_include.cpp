#include "get_numbers.hpp"
#include <iostream>
//#CXXFLAGS=-std=c++11

int main( int argc, char* argv[] )
{
    auto d1 = get_double();
    auto i1 = get_int();

    std::cout << d1 << ' ' << i1 << "\n";
}
