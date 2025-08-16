//#LINKFLAGS=-lpcap
//#F1=1
#include <cmath>
#include <iostream>
//#F2=2
//#F3=3
//#LDFLAGS=-lm

// Edge cases for magic flag pattern testing
//#PKG-CONFIG=zlib
// Invalid patterns that should NOT be detected:
// #LIBS=not_magic (space before #)
/* //#LIBS=commented_out */
// #LIBS=not_comment_magic (should be comment, not preprocessor)
//#INVALID PATTERN (no =)
// //#123=invalid_start_with_number (starts with number - invalid identifier)

int main(int argc, char* argv[])
{
    std::cout << std::abs(-2) << "\n";
}
