#include "cross_platform.hpp"
#include <iostream>

int main(int argc, char* argv[])
{
    Cross_Platform cp;
    std::cout << cp.hello_world() << " from " << cp.name() << "\n";
}
