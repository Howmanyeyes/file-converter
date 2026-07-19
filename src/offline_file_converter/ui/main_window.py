from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from offline_file_converter.i18n import load_strings
from offline_file_converter.ui.file_drop_area import FileDropArea


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._strings = load_strings()
        self.setWindowTitle(self._strings["app_name"])
        self.resize(760, 560)
        self.setMinimumSize(620, 480)

        self._drop_area = FileDropArea(self._strings)
        self._drop_area.select_files_requested.connect(self._select_files)

        privacy = QLabel(self._strings["privacy"])
        privacy.setObjectName("privacyText")
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(16)
        layout.addWidget(self._drop_area, stretch=1)
        layout.addWidget(privacy)

        content = QWidget()
        content.setLayout(layout)
        self.setCentralWidget(content)

    def _select_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self._strings["select_file"],
            "",
            self._strings["file_filter"],
        )
        if paths:
            self._drop_area.add_files(paths)
