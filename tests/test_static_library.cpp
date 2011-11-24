#include "get_numbers.hpp"
#include <iostream>

//#LINKFLAGS="-L../bin -lget_numbers"

int main(int argc, char* argv[] )
{
    std::cout << get_int() << " " << get_double() << std::endl;
    return 0;
}


