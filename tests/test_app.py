import mock
import pytest
import tests.sample_app

from pyapp.app import HandlerProxy, add_argument, CliApplication


class TestHandlerProxy(object):
    def test_basic_usage(self):
        def sample_handler():
            return "Success"

        mock_parser = mock.Mock()

        target = HandlerProxy(sample_handler, mock_parser)

        assert sample_handler is target.handler
        assert mock_parser is target.sub_parser
        assert sample_handler.__doc__ == target.__doc__
        assert sample_handler.__name__ == target.__name__
        assert sample_handler.__module__ == target.__module__
        assert target() == 'Success'

    def test_with_arguments(self):

        @add_argument('--foo', dest='foo', help='Foo option')
        @add_argument('--bar', dest='bar', help='Bar option')
        def sample_handler():
            pass

        mock_parser = mock.Mock()
        HandlerProxy(sample_handler, mock_parser)

        assert mock_parser.add_argument.call_count == 2


class TestCliApplication(object):
    def test_initialisation(self):
        target = CliApplication(tests.sample_app)

        assert target.root_module is tests.sample_app
        assert target.application_settings == 'tests.sample_app.default_settings'
        assert len(target._handlers) == 3

    def test_initialisation_alternate_settings(self):
        target = CliApplication(
            tests.sample_app,
            application_settings='tests.runtime_settings'
        )

        assert target.application_settings == 'tests.runtime_settings'

    def test_dispatch_args(self):
        closure = {}

        target = CliApplication(tests.sample_app)

        @target.register_handler(cli_name='sample')
        @add_argument('--foo', dest='foo')
        def sample_handler(opts):
            closure['opts'] = opts

        target.dispatch(args=('sample', '--foo', 'bar'))

        assert closure['opts'].foo == 'bar'

    def test_dispatch(self):
        target = tests.sample_app.__main__.app

        target.dispatch(args=('happy',))

    def test_dispatch__keyboard_interrupt(self):
        target = tests.sample_app.__main__.app

        with pytest.raises(SystemExit) as ex:
            target.dispatch(args=('cheeky',))

        assert ex.value.code == -1

    def test_dispatch__return_status(self):
        target = tests.sample_app.__main__.app

        with pytest.raises(SystemExit) as ex:
            target.dispatch(args=('sad',))

        assert ex.value.code == -2

    def test_dispatch__exception(self):
        target = tests.sample_app.__main__.app

        with pytest.raises(Exception) as ex:
            target.dispatch(args=('angry',))

        assert str(ex.value) == 'Grrrr'

    def test_loading_logging(self):
        import logging
        target = CliApplication(tests.sample_app,
                                application_settings='tests.sample_app.logging_settings')

        target.dispatch(args=('--log-level', 'WARN', 'settings'))
        assert logging.root.level == logging.WARN

    def test_env_key_settings(self):
        target = CliApplication(tests.sample_app)
        assert target.env_loglevel_key == 'PYAPP_LOGLEVEL'
        assert target.env_settings_key == 'PYAPP_SETTINGS'

        target = CliApplication(tests.sample_app, env_loglevel_key='MYAPP_LOGLEVEL', env_settings_key='MYAPP_SETTINGS')
        assert target.env_loglevel_key == 'MYAPP_LOGLEVEL'
        assert target.env_settings_key == 'MYAPP_SETTINGS'

    def test_summary(self):
        target = CliApplication(tests.sample_app, name='testing')
        assert target.application_summary == 'testing version 1.2.3'

        target = CliApplication(tests.sample_app, name='testing', description='This is a test')
        assert target.application_summary == 'testing version 1.2.3 - This is a test'
