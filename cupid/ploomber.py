from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from subprocess import PIPE

from ploomber.tasks import ScriptRunner


def _python_bin():
    """
    Get the path to the Python executable, return 'python' if unable to get it
    """
    executable = sys.executable
    return executable if executable else "python"


def _run_script_in_subprocess(interpreter, path, cwd, env):
    if isinstance(interpreter, str):
        res = subprocess.run([interpreter, str(path)], cwd=cwd, env=env, stderr=PIPE)
    else:
        res = subprocess.run(interpreter + [str(path)], cwd=cwd, env=env, stderr=PIPE)
    if res.returncode:
        stderr = res.stderr.decode()

        if "SyntaxError" in stderr:
            stderr += (
                "(Note: IPython magics are not supported in "
                "ScriptRunner, remove them or use the regular "
                "NotebookRunner)"
            )

        raise RuntimeError("Error while executing ScriptRunner:\n" f"{stderr}")


class CUPiDScriptRunner(ScriptRunner):
    """
    Similar to NotebookRunner, except it uses python to run the code,
    instead of papermill, hence, it doesn't generate an output notebook. But
    it also works by injecting a cell into the source code. Source can be
    a ``.py`` script or an ``.ipynb`` notebook. **Does not support magics.**

    Parameters
    ----------
    source: str or pathlib.Path
        Script source, if str, the content is interpreted as the actual
        script, if pathlib.Path, the content of the file is loaded. When
        loading from a str, ext_in must be passed
    product: ploomber.File
        The output file
    dag: ploomber.DAG
        A DAG to add this task to
    name: str, optional
        A str to indentify this task. Should not already exist in the dag
    params: dict, optional
        Script parameters. This are passed as the "parameters" argument
        to the papermill.execute_notebook function, by default, "product"
        and "upstream" are included
    ext_in: str, optional
        Source extension. Required if loading from a str. If source is a
        ``pathlib.Path``, the extension from the file is used.
    static_analysis : ('disabled', 'regular', 'strict'), default='regular'
        Check for various errors in the script. In 'regular' mode, it aborts
        execution if the notebook has syntax issues, or similar problems that
        would cause the code to break if executed. In 'strict' mode, it
        performs the same checks but raises an issue before starting execution
        of any task, furthermore, it verifies that the parameters cell and
        the params passed to the notebook match, thus, making the script
        behave like a function with a signature.
    local_execution : bool, optional
        Change working directory to be the parent of the script source.
        Defaults to False.

    Examples
    --------

    Spec API:

    .. code-block:: yaml
        :class: text-editor
        :name: pipeline-yaml

        tasks:
          - source: script.py
            class: ScriptRunner
            product:
                data: data.csv
                another: another.csv

    Python API:

    >>> from pathlib import Path
    >>> from ploomber import DAG
    >>> from ploomber.tasks import ScriptRunner
    >>> from ploomber.products import File
    >>> dag = DAG()
    >>> product = {'data': File('data.csv'), 'another': File('another.csv')}
    >>> _ = ScriptRunner(Path('script.py'), product, dag=dag)
    >>> _ = dag.build()
    """

    def __init__(
        self,
        source,
        product,
        dag,
        kernelspec_name=None,
        name=None,
        params=None,
        ext_in=None,
        static_analysis="regular",
        local_execution=False,
    ):
        self.kernelspec_name = kernelspec_name
        self.ext_in = ext_in

        kwargs = dict(hot_reload=dag._params.hot_reload)
        self._source = ScriptRunner._init_source(
            source,
            kwargs,
            ext_in,
            static_analysis,
            False,
            False,
        )
        self.local_execution = local_execution
        super(ScriptRunner, self).__init__(product, dag, name, params)

    def run(self):
        # regular mode: raise but not check signature
        # strict mode: called at render time
        if self.static_analysis == "regular":
            self.source._check_notebook(raise_=True, check_signature=False)

        fd, tmp = tempfile.mkstemp(".py")
        os.close(fd)

        code = "\n\n".join(
            [
                c["source"]
                for c in self.source.nb_obj_rendered.cells
                if c["cell_type"] == "code"
            ],
        )

        cwd = str(self.source.loc.parent.resolve())
        orig_env = os.environ.copy()

        if "PYTHONPATH" not in orig_env:
            orig_env["PYTHONPATH"] = cwd
        else:
            orig_env["PYTHONPATH"] += os.pathsep + cwd

        tmp = Path(tmp)
        tmp.write_text(code)

        if self.source.language == "python":
            interpreter = _python_bin()
            if self.kernelspec_name:
                interpreter = f"conda run -n {self.kernelspec_name} python".split()
        elif self.source.language == "r":
            interpreter = "Rscript"
        else:
            raise ValueError("ScriptRunner only works with Python and R scripts")

        try:
            _run_script_in_subprocess(interpreter, tmp, cwd, orig_env)
        except Exception as e:
            raise RuntimeError(
                "Error when executing task" f" {self.name!r}.",
            ) from e  # should be TaskBuildError
        finally:
            tmp.unlink()
