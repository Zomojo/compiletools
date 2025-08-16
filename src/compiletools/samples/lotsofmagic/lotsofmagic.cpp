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

/*
   Multi-line comment test cases:
   #include <stdlib.h>
   The above include should NOT be detected as it's inside a block comment.
   Also test magic flags in comments:
   //#COMMENTED_FLAG=should_not_be_detected
*/

/* Single line block comment with #include <math.h> should also be ignored */

int main(int argc, char* argv[])
{
    std::cout << std::abs(-2) << "\n";
}
