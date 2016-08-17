#pragma once
#include "widget.hpp"
#include <map>
#include <memory>
#include <string>
//#include <iostream>

// Singleton widget factory
struct widget_factory
{
    static widget_factory* instance();
    std::unique_ptr<widget> create(const std::string& name) const;

private:
    // Register of keys to functions that will do the creation of the widgets.
    std::map<std::string, std::function<std::unique_ptr<widget>()>> creator_map_;

    template <typename>
    friend struct widget_factory_registration;
};


// Create static instances of this struct to automatically create entries in the widget factory creator map.
template <typename DerivedType>
struct widget_factory_registration
{
    widget_factory_registration(const std::string& key)
    {
        //std::cout << "Registering " << key << "\n";
        widget_factory* wf    = widget_factory::instance();
        wf->creator_map_[key] = []()->std::unique_ptr<widget> 
                                  {
								       return std::unique_ptr<DerivedType>(new DerivedType());
                                  };
    }
};
