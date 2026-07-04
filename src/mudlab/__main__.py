"""Application entry point: python -m mudlab."""

import sys

from PySide6.QtWidgets import QApplication

from mudlab import APP_NAME, ORG_NAME, __version__
from mudlab.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(ORG_NAME)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
