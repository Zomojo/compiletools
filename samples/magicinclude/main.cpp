/* A more typical INCLUDE example would be /usr/include/boost
 * but for this example the important.hpp lives in a "subdir" of the current working directory"
 *
 * This test also verifies that command line "--include=subdir2 subdir3" also works
*/

//#INCLUDE=subdir
#include "important.hpp"
#include "important2.hpp"
#include "important3.hpp"

int main(int argc, char* argv[])
{

}

