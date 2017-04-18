"""
*Configuration based Instance factories*

Inversion of control style plugin factories that return an object instance
based on a named definition from configuration. Makes use of
:py:mod:`pyapp.conf` to store instance definitions in settings.

An instance definition includes both the object type as well as arguments
provided at instantiation, this can be used to provide for example connections
to different multiple different database instances (that use the same database
engine and connection library).

The default instance factory also integrates with the :py:mod:`pyapp.checks`
framework to allow checks to be executed on the instances.

Usage::

    >>> foo_factory = NamedPluginFactory('FOO')
    >>> instance = foo_factory()

or taking advantage of the factory being callable we can create a singleton
factory::

    >>> get_bar_instance = NamedSingletonPluginFactory('BAR')
    >>> # Get iron bar instance
    >>> bar = get_bar_instance('iron')

"""
from __future__ import absolute_import, unicode_literals
import six

import importlib
import threading

from pyapp import checks
from pyapp.conf import settings
from pyapp.utils import cached_property
from .bases import DefaultCache, FactoryMixin, SingletonFactoryMixin, ThreadLocalSingletonFactoryMixin

__all__ = ('NamedPluginFactory', 'NamedSingletonPluginFactory', 'ThreadLocalNamedSingletonPluginFactory')


def _import_type(type_name):
    """
    Import a type from a fully qualified module+type name

    :type type_name: str | unicode
    :rtype: type

    """
    module_name, type_name = type_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, type_name)


class NamedPluginFactory(FactoryMixin):
    """
    Factory object that generates a named instance from a definition in
    settings. Can optionally verify an instance type against a specified ABC
    (Abstract Base Class). The factory will cache imported types.

    Named instances are defined in settings using the following definition::

        MY_TYPE = {
            'default': (
                'my.module.MyClass', {
                    'param1': 123,
                    'param2': 'foo',
                }
            )
        }

    The :py:class:`NamedPluginFactory` is thread safe.

    """
    def __init__(self, setting, abc=None, default_name='default'):
        """
        Initialise a named factory.

        :param setting: Setting attribute that holds the definition of a 
            instance, this value should be an upper case.
        :param abc: The absolute base class that any new instance should be
            based on.
        :param default_name: The key within the settings to be returned as the
            default instance type if a value is not supplied.

        """
        assert isinstance(setting, six.string_types) and setting.isupper()
        self.setting = setting
        self.abc = abc
        self.default_name = default_name

        self._type_definitions = DefaultCache(self._get_type_definition)
        self._type_definitions_lock = threading.RLock()

        self._register_checks()

    @cached_property
    def _instance_definitions(self):
        return getattr(settings, self.setting, {})

    @property
    def available(self):
        """
        Defined names available in settings.
        """
        return self._instance_definitions.keys()

    def _get_type_definition(self, name):
        try:
            type_name, kwargs = self._instance_definitions[name]
        except KeyError:
            raise KeyError("Setting definition `{}` not found".format(name))

        type_ = _import_type(type_name)
        if self.abc and not issubclass(type_, self.abc):
            raise TypeError("Setting definition `{}` is not a subclass of `{}`".format(
                type_name, self.abc
            ))

        return type_, kwargs

    def get_definition(self, name=None):
        """
        Get a definition of an type and configuration values.

        :param name: Named instance definition; default value is defined by the
            ``default_name`` instance argument.
        :returns: instance_type, kwargs pair

        """
        with self._type_definitions_lock:
            return self._type_definitions[name or self.default_name]

    def create_instance(self, name=None):
        """
        Get a named instance.

        :param name: Named instance definition; default value is defined by the
            ``default_name`` instance argument.
        :returns: New instance of the named type.

        """
        instance_type, kwargs = self.get_definition(name)
        return instance_type(**kwargs)

    def _register_checks(self):
        checks.register(self)

    def checks(self, **kwargs):
        """
        Run checks to ensure settings are valid, secondly run checks against
        individual definitions in settings.

        """
        settings_ = kwargs['settings']

        # Check settings are defined
        if not hasattr(settings_, self.setting):
            return checks.Critical(
                "Instance definitions missing from settings.",
                hint="Add a {} entry into settings.".format(self.setting),
                obj="settings.{}".format(self.setting)
            )

        instance_definitions = getattr(settings_, self.setting)
        if instance_definitions is None:
            return  # Nothing is defined so end now.

        if not isinstance(instance_definitions, dict):
            return checks.Critical(
                "Instance definitions defined in settings not a dict instance.",
                hint="Change setting {} to be a dict in settings file.".format(self.setting),
                obj="settings.{}".format(self.setting)
            )

        # Take over the lock while checks are being performed
        with self._type_definitions_lock:
            # Backup definitions, replace and clear cache, this is to make it
            # easier to write checks for instances.
            instance_definitions_orig = self._instance_definitions
            try:
                self._instance_definitions = instance_definitions
                self._type_definitions.clear()

                messages = []

                # Check default is defined
                if self.default_name not in instance_definitions:
                    messages.append(checks.Warn(
                        "Default definition not defined.",
                        hint="The default instance type `{}` is not defined.".format(self.default_name),
                        obj="settings.{}".format(self.setting)
                    ))

                # Check instance definitions
                for name in instance_definitions:
                    message = self.check_instance(instance_definitions, name, **kwargs)
                    if isinstance(message, checks.CheckMessage):
                        messages.append(message)
                    elif message:
                        messages += message

                return messages

            finally:
                # Put definitions back and clear cache.
                self._instance_definitions = instance_definitions_orig
                self._type_definitions.clear()
    checks.check_name = "{obj.setting}.check_configuration"

    def check_instance(self, instance_definitions, name, **_):
        """
        Checks for individual instances.

        :param instance_definitions:
        :param name:
        :return:

        """
        definition = instance_definitions[name]
        if not isinstance(definition, (tuple, list)):
            return checks.Critical(
                "Instance definition is not a list/tuple.",
                hint="Change definition to be a list/tuple (type_name, kwargs) in settings.",
                obj='settings.{}[{}]'.format(self.setting, name)
            )

        if len(definition) != 2:
            return checks.Critical(
                "Instance definition is not a type name, kwarg (dict) pair.",
                hint="Change definition to be a list/tuple (type_name, kwargs) in settings.",
                obj='settings.{}[{}]'.format(self.setting, name)
            )

        type_name, kwargs = definition
        messages = []

        try:
            _import_type(type_name)
        except (ImportError, ValueError):
            messages.append(checks.Error(
                "Unable to import type `{}`.".format(type_name),
                hint="Check the type name in definition.",
                obj='settings.{}[{}]'.format(self.setting, name)
            ))

        if not isinstance(kwargs, dict):
            messages.append(checks.Critical(
                "Instance kwargs is not a dict.",
                hint="Change kwargs definition to be a dict.",
                obj='settings.{}[{}]'.format(self.setting, name)
            ))

        return messages


class NamedSingletonPluginFactory(SingletonFactoryMixin, NamedPluginFactory):
    """
    :py:class:`NamedPluginFactory` that provides a single instance of an object.

    This instance factory type is useful for instance types that only require
    a single instance eg database connections, web service agents.

    If your instance types are not thread safe it is recommended that the
    :py:class:`ThreadLocalNamedSingletonPluginFactory` is used.

    """


class ThreadLocalNamedSingletonPluginFactory(ThreadLocalSingletonFactoryMixin, NamedPluginFactory):
    """
    :py:class:`NamedPluginFactory` that provides a single instance of a plugin per
    thread.

    This instance factory type is useful for instance types that only require
    a single instance eg database connections, web service agents and that are
    not thread safe.

    """
