#include <iostream>

/** Note that you do _not_ want to include get_numbers.hpp in this 
 *  test situation because if you do cake will hunt down the get_double.cpp
 *  and get_int.cpp and compile then and statically compile them in.
 *  To actually test the creation of static and dynamic libraries
 *  we will just forward declare the appropriate functions. 
 *  They library is tucked away under the mylib directory to test that 
 *  the -L flag gets passed through appropriately
 *  */
 
int get_int(void);
double get_double(void);

//#LDFLAGS=-Lmylib/bin -lget_numbers
//#CXXFLAGS = -std=c++11
int main(int argc, char* argv[] )
{
    std::cout << get_int() << " " << get_double() << std::endl;
    return 0;
}


