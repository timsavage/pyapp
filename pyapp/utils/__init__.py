from __future__ import unicode_literals


def is_iterable(obj):
    """
    Determine if an object is iterable.

    :rtype: bool

    """
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return True


class cached_property(object):
    """
    A property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the
    property. (From bottle)
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value
