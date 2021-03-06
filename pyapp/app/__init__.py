"""
Application
~~~~~~~~~~~

*Application with bindings for commands*

Quick demo::

    >>> import sample
    >>> from pyapp.app import CliApplication, argument
    >>> app = CliApplication(sample)
    >>> @argument('--verbose', target='verbose', action='store_true')
    >>> @app.command()
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
import argcomplete
import argparse
import io
import logging
import logging.config
import os
import sys

from typing import Callable, Optional, Dict, Sequence, Union

from pyapp import conf
from pyapp import extensions
from pyapp.app import builtin_handlers
from pyapp.conf import settings

logger = logging.getLogger(__name__)


Handler = Callable[[argparse.Namespace], Optional[int]]


class HandlerProxy:
    """
    Proxy object that wraps a handler.
    """

    def __init__(self, handler: Handler, sub_parser: argparse.ArgumentParser):
        """
        Initialise proxy

        :param handler: Callable object that accepts a single argument.

        """
        self.handler = handler
        self.sub_parser = sub_parser

        # Copy details
        self.__doc__ = handler.__doc__
        self.__name__ = handler.__name__
        self.__module__ = handler.__module__

        # Add any existing arguments
        if hasattr(handler, "arguments__"):
            for args, kwargs in handler.arguments__:
                self.argument(*args, **kwargs)
            del handler.arguments__

    def __call__(self, *args, **kwargs):
        return self.handler(*args, **kwargs)

    def argument(self, *args, **kwargs) -> "HandlerProxy":
        """
        Add argument to proxy
        """
        self.sub_parser.add_argument(*args, **kwargs)
        return self


def argument(*args, **kwargs):
    """
    Decorator for adding arguments to a handler.

    This decorator can be used before or after the handler registration
    decorator :meth:`CliApplication.command` has been used.

    """

    def wrapper(func: Union[Handler, HandlerProxy]) -> Union[Handler, HandlerProxy]:
        if isinstance(func, HandlerProxy):
            func.argument(*args, **kwargs)
        else:
            # Add the argument to a list that will be consumed by HandlerProxy.
            if not hasattr(func, "arguments__"):
                func.arguments__ = [(args, kwargs)]
            else:
                func.arguments__.insert(0, (args, kwargs))
        return func

    return wrapper


class CliApplication:
    """
    :param root_module: The root module for this application (used for discovery of other modules)
    :param name: Name of your application; defaults to `sys.argv[0]`
    :param description: A description of your application for `--help`.
    :param version: Specify a specific version; defaults to `getattr(root_module, '__version__')`
    :param application_settings: The default settings for this application; defaults to `root_module.default_settings`
    :param application_checks: Location of application checks file; defaults to `root_module.checks` if it exists.

    """

    default_log_handler = logging.StreamHandler(sys.stderr)
    """
    Log handler applied by default to root logger.
    """

    default_log_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    """
    Log formatter applied by default to root logger handler.
    """

    env_settings_key = conf.DEFAULT_ENV_KEY
    """
    Key used to define settings file in environment.
    """

    env_loglevel_key = "PYAPP_LOGLEVEL"
    """
    Key used to define log level in environment
    """

    additional_handlers = (builtin_handlers.extensions, builtin_handlers.settings)
    """
    Handlers to be added when builtin handlers are registered.
    """

    def __init__(
        self,
        root_module,
        name: str = None,
        *,
        description: str = None,
        version: str = None,
        application_settings: str = None,
        application_checks: str = None,
        env_settings_key: str = None,
        env_loglevel_key: str = None,
        default_handler=None,
    ):
        self.root_module = root_module
        self.application_version = version or getattr(
            root_module, "__version__", "Unknown"
        )
        self._default_handler = default_handler

        def key_help(key):
            if key in os.environ:
                return f"{key} [{os.environ[key]}]"
            return key

        # Create argument parser
        self.parser = argparse.ArgumentParser(name, description=description)
        self.parser.add_argument(
            "--settings",
            dest="settings",
            help="Settings to load; either a Python module or settings URL. "
            f"Defaults to the env variable: {key_help(self.env_settings_key)}",
        )
        self.parser.add_argument(
            "--nocolor",
            dest="no_color",
            action="store_true",
            help="Disable colour output.",
        )
        self.parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s version: {self.application_version}",
        )

        # Log configuration
        self.parser.add_argument(
            "--log-level",
            dest="log_level",
            default=os.environ.get(self.env_loglevel_key, "INFO"),
            choices=("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"),
            help="Specify the log level to be used. "
            f"Defaults to env variable: {key_help(self.env_loglevel_key)}",
        )

        # Global check values
        self.parser.add_argument(
            "--checks",
            dest="checks_on_startup",
            action="store_true",
            help="Run checks on startup, any serious error will result "
            "in the application terminating.",
        )
        self.parser.add_argument(
            "--checks-level",
            dest="checks_message_level",
            default="INFO",
            choices=("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"),
            help="Minimum level of check message to display",
        )

        # Create sub parsers
        self.sub_parsers = self.parser.add_subparsers(dest="handler")

        self._handlers = {}
        self.register_builtin_handlers()

        # Determine application settings
        if application_settings is None:
            application_settings = f"{root_module.__name__}.default_settings"
        self.application_settings = application_settings

        # Determine application checks
        if application_checks is None:
            application_checks = f"{root_module.__name__}.checks"
        self.application_checks = application_checks

        # Override default value
        if env_settings_key is not None:
            self.env_settings_key = env_settings_key
        if env_loglevel_key is not None:
            self.env_loglevel_key = env_loglevel_key

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.root_module!r})"

    def __str__(self) -> str:
        return self.application_summary

    @property
    def application_name(self) -> str:
        """
        Name of the application
        """
        return self.parser.prog

    @property
    def application_summary(self) -> str:
        """
        Summary of the application, name version and description.
        """
        description = self.parser.description
        if description:
            return f"{self.application_name} version {self.application_version} - {description}"
        else:
            return f"{self.application_name} version {self.application_version}"

    def command(
        self, handler: Handler = None, cli_name: str = None, doc: str = None
    ) -> HandlerProxy:
        """
        Decorator for registering handlers.

        :param handler: Handler function
        :param cli_name: Optional name to use for CLI; defaults to the
            function name.
        :param doc: Description for help; default is taken from the handlers doc string.

        """

        def inner(func: Handler) -> HandlerProxy:
            name = cli_name or func.__name__

            # Setup sub parser
            description = doc or func.__doc__
            sub_parser = self.sub_parsers.add_parser(
                name, help=description.strip() if description else None
            )

            # Create proxy instance
            proxy = HandlerProxy(func, sub_parser)
            self._handlers[name] = proxy
            return proxy

        return inner(handler) if handler else inner

    def run_checks(
        self,
        output: io.StringIO,
        message_level: int = logging.INFO,
        tags: Sequence[str] = None,
        verbose: bool = False,
        no_color: bool = False,
        table: bool = False,
    ) -> bool:
        """
        Run application checks.

        :param output: File like object to write output to.
        :param message_level: Reporting level.
        :param tags: Specific tags to run.
        :param verbose: Display verbose output.
        :param no_color: Disable coloured output.
        :param table: Tabular output (disables verbose and colour option)

        """
        from pyapp.checks.registry import import_checks
        from pyapp.checks.report import CheckReport, TabularCheckReport

        # Import default application checks
        try:
            __import__(self.application_checks)
        except ImportError:
            pass

        # Import additional checks defined in settings.
        import_checks()

        # Note the getLevelName method returns the level code if a string level is supplied!
        message_level = logging.getLevelName(message_level)

        # Create report instance
        if table:
            return TabularCheckReport(output).run(message_level, tags)
        else:
            return CheckReport(verbose, no_color, output).run(
                message_level, tags, f"Checks for {self.application_summary}"
            )

    def register_builtin_handlers(self):
        """
        Register any built in handlers.
        """
        # Register the checks handler
        @argument(
            "-t",
            "--tag",
            dest="tags",
            action="append",
            help="Run checks associated with a tag.",
        )
        @argument(
            "--verbose", dest="verbose", action="store_true", help="Verbose output."
        )
        @argument(
            "--out",
            dest="out",
            default=sys.stdout,
            type=argparse.FileType(mode="w"),
            help="File to output check report to; default is stdout.",
        )
        @argument(
            "--table",
            dest="table",
            action="store_true",
            help="Output report in tabular format.",
        )
        @self.command(cli_name="checks", doc="Run a check report")
        def check_report(opts, **_):
            if self.run_checks(
                opts.out,
                opts.checks_message_level,
                opts.tags,
                opts.verbose,
                opts.no_color,
                opts.table,
            ):
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
        settings.configure(
            self.application_settings,
            opts.settings,
            env_settings_key=self.env_settings_key,
        )

    @staticmethod
    def configure_logging(opts):
        """
        Configure the logging framework.
        """
        if settings.LOGGING:
            logger.info("Applying logging configuration.")

            # Set a default version if not supplied by settings
            dict_config = settings.LOGGING.copy()
            dict_config.setdefault("version", 1)
            logging.config.dictConfig(dict_config)

            # Configure root log level
            logging.root.setLevel(opts.log_level)

    @staticmethod
    def configure_extensions(_):
        """
        Load/Configure extensions.
        """
        extensions.registry.load_from_settings()

        # Load settings into from extensions, do not override as
        # extensions are loaded after the main settings file so only
        # settings that do not already exist should be loaded.
        settings.load_from_loaders(extensions.registry.settings_loaders, override=False)

        # Indicate that everything is loaded and and initialisation
        # can be performed.
        extensions.registry.trigger_ready()

    def checks_on_startup(self, opts: argparse.Namespace):
        """
        Run checks on startup.
        """
        if opts.checks_on_startup:
            out = io.StringIO()

            serious_error = self.run_checks(
                out, opts.checks_message_level, None, True, False
            )
            if serious_error:
                logger.error("Check results:\n%s", out.getvalue())
                exit(4)
            else:
                logger.info("Check results:\n%s", out.getvalue())

    @staticmethod
    def exception_report(exception: BaseException, opts: argparse.Namespace):
        """
        Generate a report for any unhandled exceptions caught by the framework.
        """
        logger.exception(
            "Un-handled exception %s caught executing handler: %s",
            exception,
            opts.handler,
        )
        return False

    def default_handler(self, opts: argparse.Namespace, **_) -> int:
        """
        Handler called if no handler is specified
        """
        if self._default_handler:
            return self._default_handler(opts)
        else:
            print("No command specified!")
            self.parser.print_usage()
            return 1

    @staticmethod
    def call_handler(handler: Handler, *args, **kwargs) -> int:
        """
        Actually call the handler and return the status code.

        This allows for this method to be modified to provide additional
        functionality.
        """
        return handler(*args, **kwargs)

    def dispatch(self, args: Dict[str, str] = None) -> None:
        """
        Dispatch command to registered handler.
        """
        # Enable auto complete if available
        argcomplete.autocomplete(self.parser)
        opts = self.parser.parse_args(args)

        _set_running_application(self)

        self.pre_configure_logging(opts)
        self.configure_settings(opts)

        logger.info("Starting %s", self.application_summary)

        if opts.handler == "checks":
            # If checks command just configure extensions.
            self.configure_extensions(opts)
        else:
            # If checks handler don't configure logging or call the "checks on
            # startup" process.
            self.configure_logging(opts)
            self.checks_on_startup(opts)
            self.configure_extensions(opts)

        # Handle case where a handler is not supplied.
        if not opts.handler:
            handler = self.default_handler
        else:
            handler = self._handlers[opts.handler]

        # Dispatch to handler.
        try:
            exit_code = self.call_handler(handler, opts)

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


CURRENT_APP: CliApplication = None


def _set_running_application(app: CliApplication):
    global CURRENT_APP
    CURRENT_APP = app


def get_running_application() -> CliApplication:
    return CURRENT_APP
