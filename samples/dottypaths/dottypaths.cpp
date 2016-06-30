#include "d2/d2.hpp"

int main(int argc, char* argv[])
{
    if( f2() == 43 )
    {
        return 0;
    }
    else
    {
        throw;
    }
}
