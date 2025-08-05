#include "a_widget.hpp"
#include "widget_factory.hpp"

static widget_factory_registration<a_widget> wfr("a");

std::string a_widget::as_string() const 
{
    return "a";
}
