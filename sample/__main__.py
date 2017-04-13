from pyapp.app import CliApplication, add_argument
from pyapp.conf import settings

import sample

app = CliApplication(
    sample,
    name='PyApp Sample',
    description="Sample pyApp application."
)


@app.register_handler
@add_argument('--verbose', action='store_true')
def do_foo(opts):
    """
    Perform a foo operation.
    """
    # Use a command line argument
    if opts.verbose:
        print("Doing foo verbosely!")
    else:
        print("Doing foo.")

    # Print a message from the settings file
    print(settings.FOO_MESSAGE)


@app.register_handler(supports_auto_reload=True)
def running(opts):
    """
    Perform a foo operation.
    """
    import time

    counter = 0
    while True:
        print ("Loop: ", counter)
        counter += 1
        time.sleep(3)


if __name__ == '__main__':
    app.dispatch()
