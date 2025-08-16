#include <stdlib.h>
#include <stdio.h>
// #include "commented_out.h"
/* #include "block_commented.h" */
// Another comment with #include "also_ignored.h"

int main(int argc, char** argv)
{
    #ifdef NDEBUG
        printf("release %d\n", argc);
    #else
        printf("debug %d\n", argc);
    #endif
    return 0;
}
