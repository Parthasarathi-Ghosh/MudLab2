# GUI designs (Qt Designer)

Every GUI component of MudLab has a `.ui` file in this folder. The `.ui`
files are the source of truth for all layout and design; edit them in
Qt Designer, never by hand-coding widget layouts in Python.

## Workflow

1. Open a design in the bundled Qt Designer (no external install needed):

   ```bat
   designer.cmd src\mudlab\ui\main_window.ui
   ```

   Running `designer.cmd` without arguments opens Qt Designer empty
   (File > New for a new window/dialog/widget).

2. After saving changes, recompile all designs from the project root:

   ```bat
   build_ui.cmd
   ```

   This runs the bundled `pyside6-uic` on every `.ui` file here and
   regenerates the matching `ui_<name>.py`.

3. Application logic lives in `src\mudlab\` and uses the generated class:

   ```python
   from mudlab.ui.ui_main_window import Ui_MainWindow

   class MainWindow(QMainWindow):
       def __init__(self) -> None:
           super().__init__()
           self.ui = Ui_MainWindow()
           self.ui.setupUi(self)
   ```

## Rules

- One `.ui` file per window/dialog/widget, named after its class in
  snake_case (`main_window.ui` for `MainWindow`).
- `ui_*.py` files are generated - never edit them by hand; they are
  overwritten by `build_ui.cmd`. They are committed so the app runs
  straight after a clone.
- Widgets that Qt Designer cannot design directly (e.g. the Matplotlib
  canvas) get an empty named layout in the `.ui` as a placeholder, and
  code inserts the widget into that layout at runtime.
- `.ui` files are XML and must stay UTF-8, like everything else here.
