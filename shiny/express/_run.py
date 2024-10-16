from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import cast

from htmltools import Tag, TagList

from .. import ui
from .._app import App
from ..session import Inputs, Outputs, Session
from ._recall_context import RecallContextManager
from .display_decorator._func_displayhook import _display_decorator_function_def
from .display_decorator._node_transformers import (
    DisplayFuncsTransformer,
    display_decorator_func_name,
)

__all__ = ("wrap_express_app",)

_DEFAULT_PAGE_FUNCTION = ui.page_fluid


def wrap_express_app(file: Path | None = None) -> App:
    """Wrap a Shiny express-mode app into a Shiny `App` object.

    Parameters
    ----------
    file
        The path to the file containing the Shiny express application. If `None`, the
        `SHINY_EXPRESS_APP_FILE` environment variable is used.

    Returns
    -------
    :
        A `shiny.App` object.
    """
    if file is None:
        app_file = os.getenv("SHINY_EXPRESS_APP_FILE")
        if app_file is None:
            raise ValueError(
                "No app file was specified and the SHINY_EXPRESS_APP_FILE environment variable "
                "is not set."
            )
        file = Path(os.getcwd()) / app_file

    app_ui = run_express(file)

    def express_server(input: Inputs, output: Outputs, session: Session):
        try:
            run_express(file)

        except Exception:
            import traceback

            traceback.print_exception(*sys.exc_info())
            raise

    app = App(app_ui, express_server)

    return app


def run_express(file: Path) -> Tag | TagList:
    with open(file) as f:
        content = f.read()

    tree = ast.parse(content, file)
    tree = DisplayFuncsTransformer().visit(tree)
    tree = ast.fix_missing_locations(tree)

    ui_result: Tag | TagList = TagList()

    def set_result(x: object):
        nonlocal ui_result
        ui_result = cast(Tag, x)

    sys.displayhook = set_result

    reset_top_level_recall_context_manager()
    get_top_level_recall_context_manager().__enter__()

    file_path = str(file.resolve())

    var_context: dict[str, object] = {
        "__file__": file_path,
        display_decorator_func_name: _display_decorator_function_def,
    }

    # Execute each top-level node in the AST
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            exec(
                compile(ast.Module([node], type_ignores=[]), file_path, "exec"),
                var_context,
                var_context,
            )
        else:
            exec(
                compile(ast.Interactive([node], type_ignores=[]), file_path, "single"),
                var_context,
                var_context,
            )

    get_top_level_recall_context_manager().__exit__(None, None, None)
    return ui_result


_top_level_recall_context_manager: RecallContextManager[Tag]
_top_level_recall_context_manager_has_been_replaced = False


def reset_top_level_recall_context_manager():
    global _top_level_recall_context_manager
    global _top_level_recall_context_manager_has_been_replaced
    _top_level_recall_context_manager = RecallContextManager(_DEFAULT_PAGE_FUNCTION)
    _top_level_recall_context_manager_has_been_replaced = False


def get_top_level_recall_context_manager():
    return _top_level_recall_context_manager


def replace_top_level_recall_context_manager(
    cm: RecallContextManager[Tag],
    force: bool = False,
) -> RecallContextManager[Tag]:
    """
    Replace the current top level RecallContextManager with another one.

    This transfers the `args` and `kwargs` from the previous RecallContextManager to the
    new one. Normally it will only have an effect the first time it's run; it only
    replace the previous one if has not already been replaced. To override this
    behavior, this use `force=True`.

    Parameters
    ----------
    cm
        The RecallContextManager to replace the previous one.
    force
        If `False` (the default) and the top level RecallContextManager has already been
        replaced, return with no chnages. If `True`, this will aways replace.

    Returns
    -------
    :
        The previous top level RecallContextManager.
    """
    global _top_level_recall_context_manager
    global _top_level_recall_context_manager_has_been_replaced

    old_cm = _top_level_recall_context_manager

    if force is False and _top_level_recall_context_manager_has_been_replaced:
        return old_cm

    args = old_cm.args.copy()
    args.extend(cm.args)
    cm.args = args

    kwargs = old_cm.kwargs.copy()
    kwargs.update(cm.kwargs)
    cm.kwargs = kwargs

    old_cm.__exit__(BaseException, None, None)
    cm.__enter__()
    _top_level_recall_context_manager = cm
    _top_level_recall_context_manager_has_been_replaced = True

    return old_cm
