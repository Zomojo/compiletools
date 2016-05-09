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
    """ Traverse a tree, calling the given function on the nodes """
    function_uses_depth = 'depth' in inspect.getargspec(function).args
    for key, value in tree.items():
        if traverse_before_function_call:
            traverse(
                tree=value,
                function=function,
                traverse_before_function_call=traverse_before_function_call,
                depth=depth + 1)
        if function_uses_depth:
            function(key, depth=depth)
        else:
            function(key)
        if not traverse_before_function_call:
            traverse(
                tree=value,
                function=function,
                traverse_before_function_call=traverse_before_function_call,
                depth=depth + 1)
