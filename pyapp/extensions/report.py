from __future__ import print_function, unicode_literals

import sys

from pyapp.extensions.registry import registry
from pyapp.utils import colorama

if colorama:
    from colorama import Style, Fore


class ExtensionReport(object):
    """
    Wrapper for the generation of a check report.
    """
    width = 80

    def __init__(self, verbose=False, no_color=False, f_out=sys.stdout, extension_registry=registry):
        """
        Initialise check report

        :param verbose: Enable verbose output
        :param no_color: Disable colourised output (if colorama is installed)
        :param f_out: File to output report to; default is ``stdout``
        :param extension_registry: Registry to source extensions from; defaults to the builtin registry.

        """
        self.verbose = verbose
        self.f_out = f_out
        # Default color to be disabled if colorama is not installed.
        self.no_color = no_color if colorama else True
        self.registry = extension_registry

        # Generate templates
        if self.no_color:
            self.BASIC_TEMPLATE = "+ {name} ({version})\n"
            self.VERBOSE_TEMPLATE = \
                ("=" * self.width) + \
                "\n Name:       {name}" +  \
                "\n Version:    {version}" + \
                "\n Package:    {package}" + \
                "\n Settings:   {default_settings}" + \
                "\n Has Checks: {has_checks}\n" + \
                ("=" * self.width) + "\n\n"

        else:
            self.BASIC_TEMPLATE = Fore.YELLOW + "+" + Fore.CYAN + " {name}" + Style.RESET_ALL + " ({version})\n"
            self.VERBOSE_TEMPLATE = \
                Fore.YELLOW + ("=" * self.width) + Style.RESET_ALL + \
                Style.BRIGHT + "\n Name:       " + Style.RESET_ALL + Fore.CYAN + "{name}" + Style.RESET_ALL + \
                Style.BRIGHT + "\n Version:    " + Style.RESET_ALL + "{version}" + \
                Style.BRIGHT + "\n Package:    " + Style.RESET_ALL + "{package}" + \
                Style.BRIGHT + "\n Settings:   " + Style.RESET_ALL + "{default_settings}" + \
                Style.BRIGHT + "\n Has Checks: " + Style.RESET_ALL + "{has_checks}\n" + \
                Fore.YELLOW + ("=" * self.width) + Style.RESET_ALL + "\n\n"

    def output_result(self, extension):
        """
        Output a result to output file.

        :type extension: pyapp.extensions.register.Extension

        """
        format_args = dict(
            name=extension.name,
            version=extension.version or 'Unknown',
            package=extension.package,
            default_settings=extension.default_settings or 'None',
            has_checks='Yes' if bool(extension.checks_module) else 'No',
        )

        if self.verbose:
            self.f_out.write(self.VERBOSE_TEMPLATE.format(**format_args))
        else:
            self.f_out.write(self.BASIC_TEMPLATE.format(**format_args))

    def run(self):
        """
        Run the report
        """
        for extension in self.registry:
            self.output_result(extension)
