from collections.abc import Sequence
from importlib.resources import files

from PySide6.QtWidgets import QApplication

from offline_file_converter.ui.main_window import MainWindow


def _load_stylesheet() -> str:
    resource = files("offline_file_converter.resources.styles").joinpath("dark.qss")
    return resource.read_text(encoding="utf-8")


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing

    app = QApplication(list(argv or []))
    app.setApplicationName("Offline File Converter")
    app.setOrganizationName("Offline File Converter")
    app.setStyleSheet(_load_stylesheet())
    return app


def main() -> int:
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
