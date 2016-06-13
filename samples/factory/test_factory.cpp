#include "widget_factory.hpp"
#include <exception>
#include <iostream>

int main(int argc, char* argv[])
{
    try
    {
        auto a_widget = widget_factory::instance()->create("a");
        auto z_widget = widget_factory::instance()->create("z");

        std::cout << a_widget->as_string() << z_widget->as_string() << "\n";
    }
    catch (std::exception& ex)
    {
        std::cout << ex.what() << "\n";
        throw;
    }
}
