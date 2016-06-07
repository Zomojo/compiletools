#include "z_widget.hpp"
#include "widget_factory.hpp"

static widget_factory_registration<z_widget> wfr("z");

std::string z_widget::as_string() const 
{
    return "z";
}
