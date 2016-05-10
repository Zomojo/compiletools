from collections import defaultdict
import inspect


def tree():
    """ A tree is a dict whose default values are themselves trees """
    return defaultdict(tree)


def dicts(tt):
    """ Convert the tree to a standard dict.
        For example, to pretty print, pprint(dicts(tree_obj))
    """
    return {key: dicts(tt[key]) for key in tt}


def traverse(tree, function, traverse_before_function_call=True, depth=0):
    """ Traverse a tree, calling the given function on the nodes.
        By default the function will be passed the node key as the first argument.
        However, ff the function takes named arguments of key, value, or depth 
        those will be passed in as named arguments.
    """
    # Create the keyword arguments if they are required
    function_args = inspect.getargspec(function).args
    kwargs={}
    if 'depth' in function_args:
        kwargs['depth']=depth

    # traverse the tree recursively
    for key, value in tree.items():
        if 'key' in function_args:
            kwargs['key']=key
        if 'value' in function_args:
            kwargs['value']=value
        if traverse_before_function_call:
            traverse(
                tree=value,
                function=function,
                traverse_before_function_call=traverse_before_function_call,
                depth=depth + 1)
        if kwargs:
            function(**kwargs)
        else:
            function(key)
        if not traverse_before_function_call:
            traverse(
                tree=value,
                function=function,
                traverse_before_function_call=traverse_before_function_call,
                depth=depth + 1)
