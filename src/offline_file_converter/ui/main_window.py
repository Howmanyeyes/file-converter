from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from offline_file_converter.edition import OFFICE_SUPPORT_ENABLED
from offline_file_converter.i18n import load_strings
from offline_file_converter.settings import AppSettings
from offline_file_converter.ui.file_drop_area import FileDropArea
from offline_file_converter.ui.jpeg_actions import (
    JpegCompressAction,
    JpegMergeAction,
    JpegToPdfAction,
    JpegToPngAction,
)
from offline_file_converter.ui.office_actions import (
    OfficeToJpegAction,
    OfficeToPdfAction,
    OfficeToPngAction,
)
from offline_file_converter.ui.pdf_to_jpeg_action import PdfToJpegAction
from offline_file_converter.ui.pdf_to_png_action import PdfToPngAction
from offline_file_converter.ui.pdf_tools import (
    PdfCompressAction,
    PdfMergeAction,
    PdfSplitAction,
)
from offline_file_converter.ui.png_to_jpeg_action import PngToJpegAction
from offline_file_converter.ui.png_to_pdf_action import PngToPdfAction
from offline_file_converter.ui.png_tools import (
    PngCompressAction,
    PngMergeAction,
)
from offline_file_converter.ui.settings_window import SettingsWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._strings = load_strings()
        self.setWindowTitle(self._strings["app_name"])
        self.resize(760, 620)
        self.setMinimumSize(620, 540)

        self._settings = AppSettings(self)
        self._settings_window = SettingsWindow(
            self._settings,
            self._strings,
            OFFICE_SUPPORT_ENABLED,
        )
        self._create_application_menu()

        self._drop_area = FileDropArea(
            self._strings,
            OFFICE_SUPPORT_ENABLED,
        )
        self._drop_area.select_files_requested.connect(self._select_files)

        self._pdf_to_png_action = PdfToPngAction(self._strings)
        self._pdf_to_png_action.set_dpi(self._settings.pdf_dpi)
        self._pdf_to_png_action.set_output_directory(
            self._settings.output_directory
        )
        self._pdf_to_png_action.set_export_mode(
            self._settings.pdf_export_mode
        )
        self._drop_area.files_changed.connect(self._pdf_to_png_action.set_files)
        self._settings.pdf_dpi_changed.connect(self._pdf_to_png_action.set_dpi)
        self._settings.output_directory_changed.connect(
            self._pdf_to_png_action.set_output_directory
        )
        self._settings.pdf_export_mode_changed.connect(
            self._pdf_to_png_action.set_export_mode
        )

        self._pdf_to_jpeg_action = PdfToJpegAction(self._strings)
        self._pdf_to_jpeg_action.set_dpi(self._settings.pdf_dpi)
        self._pdf_to_jpeg_action.set_output_directory(
            self._settings.output_directory
        )
        self._pdf_to_jpeg_action.set_export_mode(
            self._settings.pdf_export_mode
        )
        self._pdf_to_jpeg_action.set_extension(
            self._settings.jpeg_extension
        )
        self._drop_area.files_changed.connect(self._pdf_to_jpeg_action.set_files)
        self._settings.pdf_dpi_changed.connect(self._pdf_to_jpeg_action.set_dpi)
        self._settings.output_directory_changed.connect(
            self._pdf_to_jpeg_action.set_output_directory
        )
        self._settings.pdf_export_mode_changed.connect(
            self._pdf_to_jpeg_action.set_export_mode
        )
        self._settings.jpeg_extension_changed.connect(
            self._pdf_to_jpeg_action.set_extension
        )
        self._pdf_to_jpeg_action.extension_selected.connect(
            self._settings.set_jpeg_extension
        )

        self._png_to_pdf_action = PngToPdfAction(self._strings)
        self._png_to_pdf_action.set_output_directory(
            self._settings.output_directory
        )
        self._drop_area.files_changed.connect(self._png_to_pdf_action.set_files)
        self._settings.output_directory_changed.connect(
            self._png_to_pdf_action.set_output_directory
        )

        self._png_to_jpeg_action = PngToJpegAction(self._strings)
        self._png_to_jpeg_action.set_output_directory(
            self._settings.output_directory
        )
        self._png_to_jpeg_action.set_extension(
            self._settings.jpeg_extension
        )
        self._drop_area.files_changed.connect(self._png_to_jpeg_action.set_files)
        self._settings.output_directory_changed.connect(
            self._png_to_jpeg_action.set_output_directory
        )
        self._settings.jpeg_extension_changed.connect(
            self._png_to_jpeg_action.set_extension
        )
        self._png_to_jpeg_action.extension_selected.connect(
            self._settings.set_jpeg_extension
        )

        self._png_compress_action = PngCompressAction(self._strings)
        self._png_merge_action = PngMergeAction(self._strings)
        for action in (
            self._png_compress_action,
            self._png_merge_action,
        ):
            action.set_output_directory(self._settings.output_directory)
            self._drop_area.files_changed.connect(action.set_files)
            self._settings.output_directory_changed.connect(
                action.set_output_directory
            )

        self._office_actions: tuple[
            OfficeToPdfAction | OfficeToPngAction | OfficeToJpegAction,
            ...,
        ] = ()
        if OFFICE_SUPPORT_ENABLED:
            self._office_to_pdf_action = OfficeToPdfAction(self._strings)
            self._office_to_png_action = OfficeToPngAction(self._strings)
            self._office_to_jpeg_action = OfficeToJpegAction(self._strings)
            self._office_to_png_action.set_dpi(self._settings.pdf_dpi)
            self._office_to_png_action.set_export_mode(
                self._settings.pdf_export_mode
            )
            self._office_to_jpeg_action.set_dpi(self._settings.pdf_dpi)
            self._office_to_jpeg_action.set_export_mode(
                self._settings.pdf_export_mode
            )
            self._office_to_jpeg_action.set_extension(
                self._settings.jpeg_extension
            )
            self._settings.pdf_dpi_changed.connect(
                self._office_to_png_action.set_dpi
            )
            self._settings.pdf_export_mode_changed.connect(
                self._office_to_png_action.set_export_mode
            )
            self._settings.pdf_dpi_changed.connect(
                self._office_to_jpeg_action.set_dpi
            )
            self._settings.pdf_export_mode_changed.connect(
                self._office_to_jpeg_action.set_export_mode
            )
            self._settings.jpeg_extension_changed.connect(
                self._office_to_jpeg_action.set_extension
            )
            self._office_actions = (
                self._office_to_pdf_action,
                self._office_to_png_action,
                self._office_to_jpeg_action,
            )
            for action in self._office_actions:
                action.set_output_directory(
                    self._settings.output_directory
                )
                self._drop_area.files_changed.connect(action.set_files)
                self._settings.output_directory_changed.connect(
                    action.set_output_directory
                )

        self._jpeg_to_png_action = JpegToPngAction(self._strings)
        self._jpeg_to_pdf_action = JpegToPdfAction(self._strings)
        self._jpeg_compress_action = JpegCompressAction(self._strings)
        self._jpeg_merge_action = JpegMergeAction(self._strings)
        for action in (
            self._jpeg_to_png_action,
            self._jpeg_to_pdf_action,
            self._jpeg_compress_action,
            self._jpeg_merge_action,
        ):
            action.set_output_directory(self._settings.output_directory)
            self._drop_area.files_changed.connect(action.set_files)
            self._settings.output_directory_changed.connect(
                action.set_output_directory
            )

        self._pdf_split_action = PdfSplitAction(self._strings)
        self._pdf_merge_action = PdfMergeAction(self._strings)
        self._pdf_compress_action = PdfCompressAction(self._strings)
        self._pdf_compress_action.set_minimum_quality(
            self._settings.pdf_min_compression_quality
        )
        self._settings.pdf_min_compression_quality_changed.connect(
            self._pdf_compress_action.set_minimum_quality
        )
        for action in (
            self._pdf_split_action,
            self._pdf_merge_action,
            self._pdf_compress_action,
        ):
            action.set_output_directory(self._settings.output_directory)
            self._drop_area.files_changed.connect(action.set_files)
            self._settings.output_directory_changed.connect(
                action.set_output_directory
            )

        actions = QWidget()
        actions_layout = QGridLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setHorizontalSpacing(12)
        actions_layout.setVerticalSpacing(10)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        actions_layout.addWidget(self._pdf_to_png_action, 0, 0)
        actions_layout.addWidget(self._pdf_to_jpeg_action, 0, 1)
        actions_layout.addWidget(self._png_to_pdf_action, 0, 0)
        actions_layout.addWidget(self._png_to_jpeg_action, 0, 1)
        actions_layout.addWidget(self._jpeg_to_png_action, 0, 0)
        actions_layout.addWidget(self._jpeg_to_pdf_action, 0, 1)
        actions_layout.addWidget(self._pdf_split_action, 1, 0)
        actions_layout.addWidget(self._pdf_merge_action, 1, 1)
        actions_layout.addWidget(self._png_compress_action, 1, 0)
        actions_layout.addWidget(self._png_merge_action, 1, 1)
        actions_layout.addWidget(self._jpeg_compress_action, 1, 0)
        actions_layout.addWidget(self._jpeg_merge_action, 1, 1)
        if OFFICE_SUPPORT_ENABLED:
            actions_layout.addWidget(self._office_to_pdf_action, 0, 0)
            actions_layout.addWidget(self._office_to_png_action, 0, 1)
            actions_layout.addWidget(
                self._office_to_jpeg_action,
                1,
                0,
                1,
                2,
                alignment=Qt.AlignmentFlag.AlignHCenter,
            )
        actions_layout.addWidget(
            self._pdf_compress_action,
            2,
            0,
            1,
            2,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        privacy = QLabel(self._strings["privacy"])
        privacy.setObjectName("privacyText")
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(16)
        layout.addWidget(self._drop_area, stretch=1)
        layout.addWidget(actions)
        layout.addWidget(privacy)

        content = QWidget()
        content.setLayout(layout)
        self.setCentralWidget(content)

    def _create_application_menu(self) -> None:
        self.menuBar().setNativeMenuBar(True)
        application_menu = self.menuBar().addMenu(
            self._strings["application_menu"]
        )

        settings_action = QAction(self._strings["settings_action"], self)
        settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        settings_action.setShortcut(
            QKeySequence(QKeySequence.StandardKey.Preferences)
        )
        settings_action.triggered.connect(self._settings_window.show_window)
        application_menu.addAction(settings_action)

    def _select_files(self) -> None:
        selected_format = self._drop_area.selected_format
        if selected_format == "pdf":
            file_filter = self._strings["pdf_file_filter"]
        elif selected_format == "png":
            file_filter = self._strings["png_file_filter"]
        elif selected_format == "jpeg":
            file_filter = self._strings["jpeg_file_filter"]
        elif selected_format == "word":
            file_filter = self._strings["word_file_filter"]
        elif selected_format == "powerpoint":
            file_filter = self._strings["powerpoint_file_filter"]
        else:
            filter_key = (
                "file_filter"
                if OFFICE_SUPPORT_ENABLED
                else "file_filter_lite"
            )
            file_filter = self._strings[filter_key]

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self._strings["select_file"],
            "",
            file_filter,
        )
        if paths:
            self._drop_area.add_files(paths)
