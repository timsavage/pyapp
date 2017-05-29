"""
Application
~~~~~~~~~~~

*Application with bindings for commands*

Quick demo::

    >>> import sample
    >>> from pyapp.app import CliApplication, add_argument
    >>> app = CliApplication(sample)

    >>> @add_argument('--verbose', target='verbose', action='store_true')
    >>> @app.register_handler()
    >>> def hello(opts):
    ...     if opts.verbose:
    ...         print("Being verbose!")
    ...     print("Hello")

    >>> if __name__ == '__main__':
    ...     app.dispatch()

This example provides an application with a command `hello` that takes an
optional `verbose` flag. The framework also provides help, configures and loads
settings (using :py:mod:`pyapp.conf`), an interface to the checks framework
and configures the Python logging framework.

There are however a few more things that are required to get this going. The
:py:class:`CliApplication` class expects a certain structure of your
application to allow for it's (customisable) defaults to be applied.

Your application should have the following structure::

    my_app/__init__.py          # Include a __version__ variable
           __main__.py          # This is where the quick demo is located
           default_settings.py  # The default settings file


CliApplication
--------------

.. autoclass:: CliApplication
    :members: register_handler, dispatch

"""
from __future__ import absolute_import, print_function, unicode_literals

import argparse
try:
    import argcomplete
except ImportError:
    argcomplete = None
import io
import logging
import logging.config
import os
import sys

from pyapp import conf
from pyapp import extensions
from pyapp.app import builtin_handlers
from pyapp.conf import settings

logger = logging.getLogger(__name__)


class HandlerProxy(object):
    """
    Proxy object that wraps a handler.
    """
    def __init__(self, handler, sub_parser):
        """
        Initialise proxy

        :param handler: Callable object that accepts a single argument.
        :type sub_parser: argparse.ArgumentParser

        """
        self.handler = handler
        self.sub_parser = sub_parser

        # Copy details
        self.__doc__ = handler.__doc__
        self.__name__ = handler.__name__
        self.__module__ = handler.__module__

        # Add any existing arguments
        if hasattr(handler, 'arguments'):
            for args, kwargs in handler.arguments:
                self.add_argument(*args, **kwargs)
            del handler.arguments

    def __call__(self, *args, **kwargs):
        return self.handler(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        """
        Add argument to proxy
        """
        self.sub_parser.add_argument(*args, **kwargs)
        return self


def add_argument(*args, **kwargs):
    """
    Decorator for adding arguments to a handler.

    This decorator can be used before or after the handler registration
    decorator :meth:`CliApplication.register_handler` has been used.

    """
    def wrapper(func):
        if isinstance(func, HandlerProxy):
            func.add_argument(*args, **kwargs)
        else:
            # Add the argument to a list that will be consumed by HandlerProxy.
            if not hasattr(func, 'arguments'):
                func.arguments = list()
            func.arguments.append((args, kwargs))
        return func
    return wrapper


class CliApplication(object):
    """
    :param root_module: The root module for this application (used for
        discovery of other modules)
    :param name: Name of your application; defaults to `sys.argv[0]`
    :param description: A description of your application for `--help`.
    :param version: Specify a specific version; defaults to
        `getattr(root_module, '__version__')`
    :param application_settings: The default settings for this application;
        defaults to `root_module.default_settings`
    :param application_checks: Location of application checks file; defaults to
        `root_module.checks` if it exists.

    """
    default_log_handler = logging.StreamHandler(sys.stderr)
    """
    Log handler applied by default to root logger.
    """

    default_log_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    """
    Log formatter applied by default to root logger handler.
    """

    env_settings_key = conf.DEFAULT_ENV_KEY
    """
    Key used to define settings file in environment.
    """

    env_loglevel_key = 'PYAPP_LOGLEVEL'
    """
    Key used to define log level in environment
    """

    additional_handlers = (
        builtin_handlers.extensions,
        builtin_handlers.settings,
    )
    """
    Handlers to be added when builtin handlers are registered.
    """

    def __init__(self, root_module, name=None, description=None, version=None,
                 application_settings=None, application_checks=None,
                 env_settings_key=None, env_loglevel_key=None):
        self.root_module = root_module
        self.application_version = version or getattr(root_module, '__version__', 'Unknown')

        def key_help(key):
            if key in os.environ:
                return '{} [{}]'.format(key, os.environ[key])
            return key

        # Create argument parser
        self.parser = argparse.ArgumentParser(name, description=description)
        self.parser.add_argument('--settings', dest='settings',
                                 help='Settings to load; either a Python module or settings URL. '
                                      'Defaults to the env variable: {}'.format(key_help(self.env_settings_key)))
        self.parser.add_argument('--nocolor', dest='no_color', action='store_true',
                                 help="Disable colour output (if colorama is installed).")
        self.parser.add_argument('--version', action='version',
                                 version='%(prog)s version: {}'.format(self.application_version))

        # Log configuration
        self.parser.add_argument('--log-level', dest='log_level',
                                 default=os.environ.get(self.env_loglevel_key, 'INFO'),
                                 choices=('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'),
                                 help='Specify the log level to be used. '
                                      'Defaults to env variable: {}'.format(key_help(self.env_loglevel_key)))

        # Global check values
        self.parser.add_argument('--checks', dest='checks_on_startup', action='store_true',
                                 help='Run checks on startup, any serious error will result '
                                      'in the application terminating.')
        self.parser.add_argument('--checks-level', dest='checks_message_level', default='INFO',
                                 choices=('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'),
                                 help='Minimum level of check message to display')

        # Create sub parsers
        self.sub_parsers = self.parser.add_subparsers(dest='handler')

        self._handlers = {}
        self.register_builtin_handlers()

        # Determine application settings
        if application_settings is None:
            application_settings = '{}.default_settings'.format(root_module.__name__)
        self.application_settings = application_settings

        # Determine application checks
        if application_checks is None:
            application_checks = '{}.checks'.format(root_module.__name__)
        self.application_checks = application_checks

        # Override default value
        if env_settings_key is not None:
            self.env_settings_key = env_settings_key
        if env_loglevel_key is not None:
            self.env_loglevel_key = env_loglevel_key

    @property
    def application_name(self):
        return self.parser.prog

    @property
    def application_summary(self):
        description = self.parser.description
        if description:
            return "{} version {} - {}".format(self.application_name, self.application_version, description)
        else:
            return "{} version {}".format(self.application_name, self.application_version)

    def command(self, handler=None, cli_name=None):
        """
        Decorator for registering handlers.

        The description for help is taken from the handlers doc string.

        :param handler: Handler function
        :param cli_name: Optional name to use for CLI; defaults to the
            function name.
        :rtype: HandlerProxy

        """
        def inner(func):
            name = cli_name or func.__name__

            # Setup sub parser
            doc = func.__doc__
            sub_parser = self.sub_parsers.add_parser(
                name, help=doc.strip() if doc else None
            )

            # Create proxy instance
            proxy = HandlerProxy(func, sub_parser)
            self._handlers[name] = proxy
            return proxy

        return inner(handler) if handler else inner

    # Renamed to command added to remain backwards compatible
    register_handler = command

    def run_checks(self, output, message_level=logging.INFO, tags=None, verbose=False, no_color=False):
        """
        Run application checks.

        :param output: File like object to write output to.
        :param message_level: Reporting level.
        :param tags: Specific tags to run.
        :param verbose: Display verbose output.
        :param no_color: Disable coloured output.

        """
        from pyapp.checks.registry import import_checks
        from pyapp.checks.report import CheckReport

        # Import default application checks
        try:
            __import__(self.application_checks)
        except ImportError:
            pass

        # Import additional checks defined in settings.
        import_checks()

        # Note the getLevelName method returns the level code if a string level is supplied!
        message_level = logging.getLevelName(message_level)
        return CheckReport(verbose, no_color, output).run(
            message_level, tags, "Checks for {}".format(self.application_summary))

    def register_builtin_handlers(self):
        """
        Register any built in handlers.
        """
        # Register the checks handler
        @add_argument('-t', '--tag', dest='tags', action='append',
                      help="Run checks associated with a tag.")
        @add_argument('--verbose', dest='verbose', action='store_true',
                      help="Verbose output.")
        @add_argument('--out', dest='out', default=sys.stdout,
                      type=argparse.FileType(mode='w'),
                      help='File to output check report to; default is stdout.')
        @self.command(cli_name='checks')
        def check_report(opts):
            """
            Run a check report.
            """
            if self.run_checks(opts.out, opts.checks_message_level, opts.tags,
                               opts.verbose, opts.no_color):
                exit(4)

        # Register any additional handlers
        for additional_handler in self.additional_handlers:
            additional_handler(self)

    def pre_configure_logging(self, opts):
        """
        Set some default logging so setting are logged.

        The main logging configuration from settings leaving us with a chicken
        and egg situation.

        """
        handler = self.default_log_handler
        handler.formatter = self.default_log_formatter

        # Apply handler to root logger and set level.
        logging.root.handlers = [handler]
        logging.root.setLevel(opts.log_level)

    def configure_settings(self, opts):
        """
        Configure settings container.
        """
        settings.configure(self.application_settings, opts.settings, env_settings_key=self.env_settings_key)

    def configure_logging(self, opts):
        """
        Configure the logging framework.
        """
        if settings.LOGGING:
            logger.info("Applying logging configuration.")

            # Set a default version if not supplied by settings
            dict_config = settings.LOGGING.copy()
            dict_config.setdefault('version', 1)
            logging.config.dictConfig(dict_config)

            # Configure root log level
            logging.root.setLevel(opts.log_level)

    def configure_extensions(self, _):
        """
        Load/Configure extensions.
        """
        extensions.registry.load_from_settings()

        # Load settings into from extensions, do not override as
        # extensions are loaded after the main settings file so only
        # settings that do not already exist should be loaded.
        settings.load_from_loaders(
            extensions.registry.settings_loaders,
            override=False
        )

        # Indicate that everything is loaded and and initialisation
        # can be performed.
        extensions.registry.trigger_ready()

    def checks_on_startup(self, opts):
        """
        Run checks on startup.
        """
        if opts.checks_on_startup:
            out = io.StringIO()

            serious_error = self.run_checks(out, opts.checks_message_level, None, True, False)
            if serious_error:
                logger.error("Check results:\n%s", out.getvalue())
                exit(4)
            else:
                logger.info("Check results:\n%s", out.getvalue())

    def exception_report(self, exception, opts):
        """
        Generate a report for any unhandled exceptions caught by the framework.
        """
        logger.exception("Un-handled exception %s caught executing handler: %s", exception, opts.handler)
        return False

    def dispatch(self, args=None):
        """
        Dispatch command to registered handler.
        """
        # Enable auto complete if available
        if argcomplete:
            argcomplete.autocomplete(self.parser)

        opts = self.parser.parse_args(args)

        self.pre_configure_logging(opts)
        self.configure_settings(opts)

        logger.info("Starting %s", self.application_summary)

        if opts.handler == 'checks':
            # If checks command just configure extensions.
            self.configure_extensions(opts)
        else:
            # If checks handler don't configure logging or call the "checks on
            # startup" process.
            self.configure_logging(opts)
            self.checks_on_startup(opts)
            self.configure_extensions(opts)

        # Dispatch to handler.
        try:
            exit_code = self._handlers[opts.handler](opts)

        except Exception as ex:
            if not self.exception_report(ex, opts):
                raise

        except KeyboardInterrupt:
            print("\n\nInterrupted.", file=sys.stderr)
            exit(-1)

        else:
            # Provide exit code.
            if exit_code:
                exit(exit_code)
