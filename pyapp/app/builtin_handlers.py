import argparse
import sys


def extensions(app):
    from pyapp.app import add_argument

    # Register extension report handler
    @add_argument('--verbose', dest='verbose', action='store_true',
                  help="Verbose output.")
    @add_argument('--out', dest='out', default=sys.stdout,
                  type=argparse.FileType(mode='w'),
                  help='File to output extension report to; default is stdout.')
    def _handler(opts):
        """
        Report of installed PyApp extensions.
        """
        from pyapp.extensions.report import ExtensionReport
        return ExtensionReport(opts.verbose, opts.no_color, opts.out).run()

    app.command(_handler, cli_name='extensions')


def settings(app):
    from pyapp.app import add_argument

    # Register settings report handler
    @add_argument('--out', dest='out', default=sys.stdout,
                  type=argparse.FileType(mode='w'),
                  help='File to output settings report to; default is stdout.')
    def _handler(opts):
        """
        Report of current settings.
        """
        from pyapp.conf.report import SettingsReport
        return SettingsReport(False, opts.no_color, opts.out).run()

    app.command(_handler, cli_name='settings')
