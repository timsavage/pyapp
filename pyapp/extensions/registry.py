from __future__ import absolute_import, unicode_literals

import importlib
import six

from types import ModuleType

from pyapp.conf import settings, factory as loader_factory
from pyapp.utils import cached_property

__all__ = ('registry', 'load')


class Extension(object):
    """
    Wrapper that provides accessors to extension module values.
    """
    def __init__(self, module, package):
        self.module = module
        self.package = package

    def __eq__(self, other):
        if isinstance(other, ModuleType):
            return self.module == other
        return NotImplemented

    def summary(self):
        return {
            'name': self.name,
            'version': self.version,
            'package': self.package,
            'checks': self.checks_module,
            'default_settings': self.default_settings
        }

    def trigger_ready(self):
        """
        Trigger the ready callback to indicate extensions have been loaded and marked as ready.
        """
        if self.ready_callback:
            self.ready_callback()

    def _resolve_name(self, name):
        """
        Return the absolute name of the module to be imported.
        """
        if isinstance(name, six.string_types):
            if name.startswith('.'):
                return self.package + name
            return name

    @cached_property
    def name(self):
        return getattr(self.module, '__package_name__', self.module.__name__)

    @cached_property
    def version(self):
        return getattr(self.module, '__version__', None)

    @cached_property
    def checks_module(self):
        return self._resolve_name(getattr(self.module, '__checks__', None))

    @cached_property
    def default_settings(self):
        return self._resolve_name(getattr(self.module, '__default_settings__', None))

    @cached_property
    def ready_callback(self):
        return getattr(self.module, 'ready', None)


class ExtensionRegistry(object):
    """
    Registry for tracking install PyApp extensions.
    """
    def __init__(self):
        self._extensions = []

    def __iter__(self):
        return iter(self._extensions)

    def load(self, module_name):
        """
        Load a module from

        :param module_name: Name of the module to load (in standard python dot format)
        :raises: ImportError

        """
        module = importlib.import_module(module_name)
        if module not in self._extensions:
            self._extensions.append(Extension(module, module_name))

    def load_from_settings(self):
        """
        Load all extensions defined in settings
        """
        for module_name in settings.EXT:
            self.load(module_name)

    def summary(self):
        """
        Returns a summary of the loaded extension modules.
        """
        module_summary = []
        for extension in self._extensions:
            module_summary.append(extension.summary())
        return module_summary

    def trigger_ready(self):
        """
        Trigger ready callback on all extension modules.
        """
        for extension in self._extensions:
            extension.trigger_ready()

    @property
    def settings_loaders(self):
        """
        Return a list of module loaders for extensions that specify default settings.
        """
        return [loader_factory(module.default_settings)
                for module in self._extensions if module.default_settings]

    @property
    def check_locations(self):
        """
        Return a list of checks modules for extensions that specify checks.
        """
        return [module.checks_module for module in self._extensions if module.checks_module]

# Shortcuts and global extension registry.
registry = ExtensionRegistry()
load = registry.load
