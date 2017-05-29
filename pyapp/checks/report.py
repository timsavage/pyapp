from __future__ import print_function, unicode_literals

import logging
import sys
import textwrap

from pyapp.checks.registry import registry
from pyapp.utils import colorama

if colorama:
    from colorama import Style, Fore, Back
    COLOURS = {
        # Type: (Title, Border),
        logging.CRITICAL: (Fore.WHITE + Back.RED, Fore.RED),
        logging.ERROR: (Fore.RED, Fore.RED),
        logging.WARNING: (Fore.YELLOW, Fore.YELLOW),
        logging.INFO: (Fore.CYAN, Fore.CYAN),
        logging.DEBUG: (Fore.MAGENTA, Fore.MAGENTA),
    }


class CheckReport(object):
    """
    Wrapper for the generation of a check report.
    """
    width = 80

    def __init__(self, verbose=False, no_color=False, f_out=sys.stdout, check_registry=registry):
        """
        Initialise check report

        :param verbose: Enable verbose output
        :param no_color: Disable colourised output (if colorama is installed)
        :param f_out: File to output report to; default is ``stdout``
        :param check_registry: Registry to source checks from; defaults to the builtin registry.

        """
        self.verbose = verbose
        self.f_out = f_out
        # Default color to be disabled if colorama is not installed.
        self.no_color = no_color if colorama else True
        self.registry = check_registry

        # Generate templates
        if self.no_color:
            self.VERBOSE_CHECK_TEMPLATE = "+ {name}\n"
            self.TITLE_TEMPLATE = " {level}: {title}"
            self.HINT_TEMPLATE = ("-" * self.width) + "\n HINT: {hint}\n"
            self.MESSAGE_TEMPLATE = ("=" * self.width) + "\n{title}\n{hint}" + ("=" * self.width) + '\n\n'

        else:
            self.VERBOSE_CHECK_TEMPLATE = Fore.YELLOW + "+ " + Fore.CYAN + "{name}\n" + Style.RESET_ALL
            self.TITLE_TEMPLATE = "{style} " + Style.BRIGHT + "{level}:" + Style.NORMAL + " {title}" + Style.RESET_ALL
            self.HINT_TEMPLATE = \
                "{border_style}" + ("-" * self.width) + Style.RESET_ALL + \
                "\n" + Style.BRIGHT + " HINT: " + Style.DIM + Fore.WHITE + " {hint}" + Style.RESET_ALL + "\n"
            self.MESSAGE_TEMPLATE = \
                "{border_style}" + ("=" * self.width) + Style.RESET_ALL + \
                "\n{title}\n{hint}" + \
                "{border_style}" + ("=" * self.width) + Style.RESET_ALL + \
                "\n\n"

    def pre_callback(self, obj):
        if self.verbose:
            check = obj.checks if hasattr(obj, 'checks') else obj
            name = getattr(check, 'check_name', check.__name__).format(obj=obj)
            self.f_out.write(self.VERBOSE_CHECK_TEMPLATE.format(name=name))

    def wrap_text(self, text, indent_width, line_sep='\n'):
        """
        Perform word wrapping on text

        :param text: Text to wrap.
        :type text: str
        :indent_width indent: Size of text indent.
        :type indent_width: int
        :param line_sep: Line separator
        :rtype: str

        """
        indent = ' ' * (indent_width + 1)
        lines = textwrap.wrap(
            text, self.width - 2,
            initial_indent=indent, subsequent_indent=indent
        )
        return line_sep.join(l + (' ' * (self.width - len(l))) for l in lines)

    def format_title(self, message):
        """
        Format the title of message.
        """
        # Get strings
        level_name = logging.getLevelName(message.level)
        msg = message.msg
        if message.obj:
            msg = "{} - {}".format(message.obj, msg)

        if self.no_color:
            title_style = ''
            line_sep = "\n"
        else:
            title_style = COLOURS[message.level][0]
            line_sep = Style.RESET_ALL + "\n" + title_style

        return self.TITLE_TEMPLATE.format(
            style=title_style, level=level_name,
            title=self.wrap_text(msg, len(level_name) + 2, line_sep).lstrip()
        )

    def format_hint(self, message):
        """
        Format the hint of a message.
        """
        hint = message.hint

        if hint:
            # Normalise to a list
            if not isinstance(hint, (list, tuple)):
                hint = (hint,)

            if self.no_color:
                line_sep = "\n"
                border_style = ""
            else:
                line_sep = Style.RESET_ALL + "\n" + Style.DIM + Fore.WHITE
                border_style = COLOURS[message.level][1]

            indent_width = len(" Hint: ")
            return self.HINT_TEMPLATE.format(
                border_style=border_style,
                hint='\n\n'.join(self.wrap_text(p, indent_width, line_sep) for p in hint).lstrip()
            )
        else:
            return ''

    def output_result(self, message):
        """
        Output a result to output file.

        :type message: messages.CheckMessage

        """
        format_args = dict(
            level=logging.getLevelName(message.level),
            title=self.format_title(message),
            hint=self.format_hint(message),
        )
        if not self.no_color:
            format_args.update(border_style=COLOURS[message.level][1])

        self.f_out.write(self.MESSAGE_TEMPLATE.format(**format_args))

    def run(self, message_level=logging.INFO, tags=None, header=None):
        """
        Run the report

        :param message_level: Level of message to be displayed.
        :type message_level: int
        :param tags: List of tags to include in report
        :type tags: list(str)
        :param header: An optional header to prepend to report (if verbose)
        :type header: str | unicode
        :return: Indicate if any serious message where generated.
        :rtype: bool

        """
        serious_message = False

        if header and self.verbose:
            self.f_out.write(header + '\n')

        # Generate report
        for messages in self.registry.run_checks_iter(tags, self.pre_callback):
            message_shown = False
            if messages:
                for message in messages:
                    serious_message = serious_message or message.is_serious()

                    # Filter output
                    if message.level >= message_level:
                        message_shown = True
                        self.output_result(message)

            if not (self.verbose or message_shown):  # DeMorgans law: !a & !b == !(a | b)
                self.f_out.write(".\n")

        return serious_message
