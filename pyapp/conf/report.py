from __future__ import print_function, unicode_literals

import sys
import pprint

from pyapp import conf
from pyapp.utils import colorama

if colorama:
    from colorama import Style, Fore


class SettingsReport(object):
    """
    Report of all settings in use.
    """
    width = 80

    def __init__(self, verbose=False, no_color=False, f_out=sys.stdout, settings=None):
        """
        Initialise check report

        :param verbose: Enable verbose output
        :param no_color: Disable colourised output (if colorama is installed)
        :param f_out: File to output report to; default is ``stdout``
        :param settings: Settings to produce a report of.

        """
        self.verbose = verbose
        self.f_out = f_out
        # Default color to be disabled if colorama is not installed.
        self.no_color = no_color if colorama else True
        self.settings = settings or conf.settings

        # Generate templates
        if self.no_color:
            self.BASIC_TEMPLATE = "{key:20} : {ppsetting}\n"

        else:
            self.BASIC_TEMPLATE = Fore.YELLOW + "{key:20} : " + Fore.CYAN + "{ppsetting}" + Style.RESET_ALL + "\n"

    def output_result(self, key, setting):
        """
        Output a result to output file.
        """
        format_args = dict(
            key=key,
            setting=setting,
            ppsetting=pprint.pformat(setting, 2)
        )

        self.f_out.write(self.BASIC_TEMPLATE.format(**format_args))

    def run(self):
        """
        Run the report
        """
        for key, setting in self.settings.__dict__.items():
            if key.isupper():
                self.output_result(key, setting)
