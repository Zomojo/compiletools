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


def depth_first_traverse(
        tree,
        pre_traverse_function=None,
        post_traverse_function=None,
        depth=0):
    """ Traverse a tree, calling the given pre/post functions on the nodes.
        By default the function will be passed the node key as the first argument.
        However, if the function takes named arguments of key, value, or depth
        those will be passed in as named arguments.
    """
    # Create the keyword arguments if they are required
    pre_kwargs = {}
    pre_function_args = {}
    if pre_traverse_function:
        pre_function_args = inspect.getargspec(pre_traverse_function).args
        if 'depth' in pre_function_args:
            pre_kwargs['depth'] = depth

    post_kwargs = {}
    post_function_args = []
    if post_traverse_function:
        post_function_args = inspect.getargspec(post_traverse_function).args
        if 'depth' in post_function_args:
            post_kwargs['depth'] = depth

    def _call_function(function, function_args, key, value, kwargs):
        """ Helper function to save copy'n'paste for pre/post variations """
        if function:
            if 'key' in function_args:
                kwargs['key'] = key
            if 'value' in function_args:
                kwargs['value'] = value
            if kwargs:
                function(**kwargs)
            else:
                function(key)

    # traverse the tree recursively
    for key, value in tree.items():
        _call_function(
            pre_traverse_function,
            pre_function_args,
            key,
            value,
            pre_kwargs)
        depth_first_traverse(
            tree=value,
            pre_traverse_function=pre_traverse_function,
            post_traverse_function=post_traverse_function,
            depth=depth + 1)
        _call_function(
            post_traverse_function,
            post_function_args,
            key,
            value,
            post_kwargs)
