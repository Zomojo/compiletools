#include "widget_factory.hpp"


widget_factory* widget_factory::instance()
{
    static widget_factory instance_;
    return &instance_;
}

std::unique_ptr<widget> widget_factory::create(const std::string& name) const
{
    //std::cout << "Create " << name << "\n";
    return creator_map_.at(name)(); 
}
