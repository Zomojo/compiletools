from collections import defaultdict

def tree():
    """ A tree is a dict whose default values are themselves trees """
    return defaultdict(tree)

def dicts(tt):
    """ Convert the tree to a standard dict.
        For example, to pretty print, pprint(dicts(tree_obj))
    """
    return {key: dicts(tt[key]) for key in tt}
