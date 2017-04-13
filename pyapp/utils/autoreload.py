import subprocess
import sys
import time
import os
import _thread

RUN_RELOADER = True

FILE_MODIFIED = 1

_mtimes = {}
_win = (sys.platform == "win32")
_cached_modules = set()
_cached_filenames = []


def clean_files(filelist):
    filenames = []
    for filename in filelist:
        if not filename:
            continue
        if filename.endswith(".pyc") or filename.endswith(".pyo"):
            filename = filename[:-1]
        if filename.endswith("$py.class"):
            filename = filename[:-9] + ".py"
        if os.path.exists(filename):
            filenames.append(filename)
    return filenames


def gen_filenames(only_new=False):
    """
    Return a list of filenames referenced in sys.modules and translation files.
    """
    # N.B. ``list(...)`` is needed, because this runs in parallel with
    # application code which might be mutating ``sys.modules``, and this will
    # fail with RuntimeError: cannot mutate dictionary while iterating
    global _cached_modules, _cached_filenames
    module_values = set(sys.modules.values())
    _cached_filenames = clean_files(_cached_filenames)
    if _cached_modules == module_values:
        # No changes in module list, short-circuit the function
        if only_new:
            return []
        else:
            return _cached_filenames

    new_modules = module_values - _cached_modules
    new_filenames = clean_files(
        [filename.__file__ for filename in new_modules
         if hasattr(filename, '__file__')])

    _cached_modules = _cached_modules.union(new_modules)
    _cached_filenames += new_filenames
    if only_new:
        return new_filenames
    else:
        return _cached_filenames


def code_changed():
    global _mtimes, _win
    for filename in gen_filenames():
        stat = os.stat(filename)
        mtime = stat.st_mtime
        if _win:
            mtime -= stat.st_ctime
        if filename not in _mtimes:
            _mtimes[filename] = mtime
            continue
        if mtime != _mtimes[filename]:
            _mtimes = {}
            return FILE_MODIFIED
    return False


def reloader_thread():
    while RUN_RELOADER:
        change = code_changed()
        if change == FILE_MODIFIED:
            sys.exit(3)  # force reload
        time.sleep(1)


def restart_with_reloader():
    while True:
        args = [sys.executable] + ['-W%s' % o for o in sys.warnoptions] + sys.argv
        new_environ = os.environ.copy()
        new_environ["RUN_MAIN"] = 'true'
        exit_code = subprocess.call(args, env=new_environ)
        if exit_code != 3:
            return exit_code


def python_reloader(main_func, args, kwargs):
    if os.environ.get("RUN_MAIN") == "true":
        _thread.start_new_thread(main_func, args, kwargs)
        try:
            reloader_thread()
        except KeyboardInterrupt:
            pass
    else:
        try:
            exit_code = restart_with_reloader()
            if exit_code < 0:
                os.kill(os.getpid(), -exit_code)
            else:
                sys.exit(exit_code)
        except KeyboardInterrupt:
            pass


def main(main_func, args, kwargs):
    python_reloader(main_func, args, kwargs)
