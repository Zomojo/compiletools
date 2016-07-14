"""  This module contains a very simple tree implementation and utility functions
    using it.  For a quick tutorial on this autovivification technique see
    https://gist.github.com/hrldcpr/2012250
"""
from __future__ import unicode_literals

import inspect
from collections import defaultdict


def tree():
    """ A tree is a dict whose default values are themselves trees """
    return defaultdict(tree)


def dicts(tree_):
    """ Convert the tree to a standard dict.
        For example, to pretty print, pprint(tree.dicts(tree_obj))
    """
    return {key: dicts(tree_[key]) for key in tree_}


def flatten(tree_):
    """ Convert a tree to a set of the keys """
    flat = set()
    for key in tree_:
        flat.add(key)
        flat |= flatten(tree_[key])

    return flat


def depth_first_traverse(
        node,
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
    for key, value in list(node.items()):
        _call_function(
            pre_traverse_function,
            pre_function_args,
            key,
            value,
            pre_kwargs)
        depth_first_traverse(
            node=value,
            pre_traverse_function=pre_traverse_function,
            post_traverse_function=post_traverse_function,
            depth=depth + 1)
        _call_function(
            post_traverse_function,
            post_function_args,
            key,
            value,
            post_kwargs)


class InTree(object):
    """" Initialize with a tree then when you call it with a key
         it will return whether or not the key exists in the tree.
    """

    def __init__(self, tree_):
        self.tree = tree_
        self.key = None
        self.result = False

    def __call__(self, key):
        self.key = key
        depth_first_traverse(
            node=self.tree,
            pre_traverse_function=self._has_key)
        return self.result

    def _has_key(self, key):
        """ This is called recursively over the tree.
            Returns true if the given key matches any of the keys in the tree.
        """
        self.result = self.result or (key == self.key)
