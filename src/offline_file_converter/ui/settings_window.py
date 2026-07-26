from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from offline_file_converter.settings import AppSettings


class SettingsWindow(QDialog):
    def __init__(
        self,
        settings: AppSettings,
        strings: dict[str, str],
        office_support_enabled: bool = True,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._strings = strings
        self._office_support_enabled = office_support_enabled

        self.setObjectName("settingsWindow")
        self.setWindowTitle(self._strings["settings_title"])
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(620, 540)
        self.resize(660, 580)

        title = QLabel(self._strings["settings_title"])
        title.setObjectName("settingsTitle")

        description = QLabel(self._strings["settings_description"])
        description.setObjectName("settingsDescription")
        description.setWordWrap(True)

        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")
        tabs.addTab(
            self._create_general_page(),
            self._strings["settings_tab_general"],
        )
        tabs.addTab(
            self._create_formats_page(),
            self._strings["settings_tab_formats"],
        )

        saved_hint = QLabel(self._strings["settings_saved_automatically"])
        saved_hint.setObjectName("settingsSavedHint")
        saved_hint.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(tabs, stretch=1)
        layout.addWidget(saved_hint)

        self._settings.pdf_dpi_changed.connect(self._sync_pdf_dpi)
        self._settings.pdf_export_mode_changed.connect(
            self._sync_pdf_export_mode
        )
        self._settings.pdf_min_compression_quality_changed.connect(
            self._sync_pdf_min_compression_quality
        )
        self._settings.jpeg_extension_changed.connect(
            self._sync_jpeg_extension
        )
        self._settings.output_directory_changed.connect(
            self._sync_output_directory
        )

    def _create_general_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(12)

        section, section_layout = self._create_section(
            self._strings["settings_general_saving"],
            self._strings["settings_general_saving_description"],
        )

        self._output_mode_combo = QComboBox()
        self._output_mode_combo.setObjectName("outputLocationCombo")
        self._output_mode_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._output_mode_combo.addItem(
            self._strings["settings_output_source"],
            "source",
        )
        self._output_mode_combo.addItem(
            self._strings["settings_output_custom"],
            "custom",
        )
        section_layout.addWidget(self._output_mode_combo)

        self._custom_output_row = QWidget()
        self._custom_output_row.setObjectName("settingsOutputRow")
        output_row_layout = QHBoxLayout(self._custom_output_row)
        output_row_layout.setContentsMargins(0, 0, 0, 0)
        output_row_layout.setSpacing(10)

        self._output_path_label = QLabel()
        self._output_path_label.setObjectName("settingsOutputPath")
        self._output_path_label.setWordWrap(True)
        self._output_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._output_path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._choose_output_button = QPushButton(
            self._strings["settings_choose_directory"]
        )
        self._choose_output_button.setObjectName("settingsChooseDirectory")
        self._choose_output_button.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self._choose_output_button.clicked.connect(self._choose_output_directory)

        output_row_layout.addWidget(self._output_path_label, stretch=1)
        output_row_layout.addWidget(
            self._choose_output_button,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        section_layout.addWidget(self._custom_output_row)

        self._sync_output_directory(self._settings.output_directory)
        self._output_mode_combo.currentIndexChanged.connect(
            self._output_mode_changed
        )

        page_layout.addWidget(section)
        page_layout.addStretch(1)
        return page

    def _create_formats_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("settingsScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("settingsScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        pdf_section, pdf_layout = self._create_section(
            self._strings["settings_pdf_section"],
            self._strings["settings_pdf_section_description"],
        )

        dpi_label = QLabel(self._strings["settings_pdf_dpi"])
        dpi_label.setObjectName("settingsFieldLabel")
        pdf_layout.addWidget(dpi_label)

        self._dpi_combo = QComboBox()
        self._dpi_combo.setObjectName("pdfDpiCombo")
        self._dpi_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        for dpi in AppSettings.PDF_DPI_OPTIONS:
            self._dpi_combo.addItem(
                self._strings[f"settings_pdf_dpi_{dpi}"],
                dpi,
            )
        current_dpi_index = self._dpi_combo.findData(self._settings.pdf_dpi)
        self._dpi_combo.setCurrentIndex(max(0, current_dpi_index))
        self._dpi_combo.currentIndexChanged.connect(self._save_pdf_dpi)
        pdf_layout.addWidget(self._dpi_combo)

        dpi_description = QLabel(self._strings["settings_pdf_dpi_description"])
        dpi_description.setObjectName("settingsFieldDescription")
        dpi_description.setWordWrap(True)
        pdf_layout.addWidget(dpi_description)

        export_label = QLabel(self._strings["settings_pdf_export"])
        export_label.setObjectName("settingsFieldLabel")
        pdf_layout.addWidget(export_label)

        self._pdf_export_combo = QComboBox()
        self._pdf_export_combo.setObjectName("pdfExportCombo")
        self._pdf_export_combo.addItem(
            self._strings["settings_pdf_export_single"],
            "single",
        )
        self._pdf_export_combo.addItem(
            self._strings["settings_pdf_export_separate"],
            "separate",
        )
        current_export_index = self._pdf_export_combo.findData(
            self._settings.pdf_export_mode
        )
        self._pdf_export_combo.setCurrentIndex(max(0, current_export_index))
        self._pdf_export_combo.currentIndexChanged.connect(
            self._save_pdf_export_mode
        )
        pdf_layout.addWidget(self._pdf_export_combo)

        export_description = QLabel(
            self._strings["settings_pdf_export_description"]
        )
        export_description.setObjectName("settingsFieldDescription")
        export_description.setWordWrap(True)
        pdf_layout.addWidget(export_description)

        compression_quality_label = QLabel(
            self._strings["settings_pdf_compression_quality"]
        )
        compression_quality_label.setObjectName("settingsFieldLabel")
        pdf_layout.addWidget(compression_quality_label)

        self._pdf_compression_quality_combo = QComboBox()
        self._pdf_compression_quality_combo.setObjectName(
            "pdfCompressionQualityCombo"
        )
        self._pdf_compression_quality_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        for quality in AppSettings.PDF_MIN_COMPRESSION_QUALITY_OPTIONS:
            self._pdf_compression_quality_combo.addItem(
                self._strings[
                    f"settings_pdf_compression_quality_{quality}"
                ],
                quality,
            )
        current_quality_index = (
            self._pdf_compression_quality_combo.findData(
                self._settings.pdf_min_compression_quality
            )
        )
        self._pdf_compression_quality_combo.setCurrentIndex(
            max(0, current_quality_index)
        )
        self._pdf_compression_quality_combo.currentIndexChanged.connect(
            self._save_pdf_min_compression_quality
        )
        pdf_layout.addWidget(self._pdf_compression_quality_combo)

        compression_quality_description = QLabel(
            self._strings["settings_pdf_compression_quality_description"]
        )
        compression_quality_description.setObjectName(
            "settingsFieldDescription"
        )
        compression_quality_description.setWordWrap(True)
        pdf_layout.addWidget(compression_quality_description)

        png_section, _png_layout = self._create_section(
            self._strings["settings_png_section"],
            self._strings["settings_png_section_description"],
        )

        jpeg_section, jpeg_layout = self._create_section(
            self._strings["settings_jpeg_section"],
            self._strings["settings_jpeg_section_description"],
        )

        jpeg_extension_label = QLabel(
            self._strings["settings_jpeg_extension"]
        )
        jpeg_extension_label.setObjectName("settingsFieldLabel")
        jpeg_layout.addWidget(jpeg_extension_label)

        self._jpeg_extension_combo = QComboBox()
        self._jpeg_extension_combo.setObjectName("jpegExtensionCombo")
        self._jpeg_extension_combo.addItem(
            self._strings["settings_jpeg_extension_jpg"],
            "jpg",
        )
        self._jpeg_extension_combo.addItem(
            self._strings["settings_jpeg_extension_jpeg"],
            "jpeg",
        )
        current_jpeg_extension_index = self._jpeg_extension_combo.findData(
            self._settings.jpeg_extension
        )
        self._jpeg_extension_combo.setCurrentIndex(
            max(0, current_jpeg_extension_index)
        )
        self._jpeg_extension_combo.currentIndexChanged.connect(
            self._save_jpeg_extension
        )
        jpeg_layout.addWidget(self._jpeg_extension_combo)

        jpeg_extension_description = QLabel(
            self._strings["settings_jpeg_extension_description"]
        )
        jpeg_extension_description.setObjectName(
            "settingsFieldDescription"
        )
        jpeg_extension_description.setWordWrap(True)
        jpeg_layout.addWidget(jpeg_extension_description)

        content_layout.addWidget(pdf_section)
        content_layout.addWidget(png_section)
        content_layout.addWidget(jpeg_section)
        if self._office_support_enabled:
            word_section, _word_layout = self._create_section(
                self._strings["settings_word_section"],
                self._strings["settings_word_section_description"],
            )
            powerpoint_section, _powerpoint_layout = self._create_section(
                self._strings["settings_powerpoint_section"],
                self._strings[
                    "settings_powerpoint_section_description"
                ],
            )
            content_layout.addWidget(word_section)
            content_layout.addWidget(powerpoint_section)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    def _create_section(
        self,
        title_text: str,
        description_text: str,
    ) -> tuple[QFrame, QVBoxLayout]:
        section = QFrame()
        section.setObjectName("settingsSection")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(18, 16, 18, 16)
        section_layout.setSpacing(9)

        title = QLabel(title_text)
        title.setObjectName("settingsSectionTitle")
        title.setWordWrap(True)

        description = QLabel(description_text)
        description.setObjectName("settingsSectionDescription")
        description.setWordWrap(True)

        section_layout.addWidget(title)
        section_layout.addWidget(description)
        return section, section_layout

    def show_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    @Slot(int)
    def _save_pdf_dpi(self, index: int) -> None:
        dpi = self._dpi_combo.itemData(index)
        if isinstance(dpi, int):
            self._settings.set_pdf_dpi(dpi)

    @Slot(int)
    def _sync_pdf_dpi(self, dpi: int) -> None:
        index = self._dpi_combo.findData(dpi)
        if index >= 0 and index != self._dpi_combo.currentIndex():
            self._dpi_combo.setCurrentIndex(index)

    @Slot(int)
    def _save_pdf_export_mode(self, index: int) -> None:
        mode = self._pdf_export_combo.itemData(index)
        if isinstance(mode, str):
            self._settings.set_pdf_export_mode(mode)

    @Slot(str)
    def _sync_pdf_export_mode(self, mode: str) -> None:
        index = self._pdf_export_combo.findData(mode)
        if index >= 0 and index != self._pdf_export_combo.currentIndex():
            self._pdf_export_combo.setCurrentIndex(index)

    @Slot(int)
    def _save_pdf_min_compression_quality(self, index: int) -> None:
        quality = self._pdf_compression_quality_combo.itemData(index)
        if isinstance(quality, int):
            self._settings.set_pdf_min_compression_quality(quality)

    @Slot(int)
    def _sync_pdf_min_compression_quality(self, quality: int) -> None:
        index = self._pdf_compression_quality_combo.findData(quality)
        if (
            index >= 0
            and index != self._pdf_compression_quality_combo.currentIndex()
        ):
            self._pdf_compression_quality_combo.setCurrentIndex(index)

    @Slot(int)
    def _save_jpeg_extension(self, index: int) -> None:
        extension = self._jpeg_extension_combo.itemData(index)
        if isinstance(extension, str):
            self._settings.set_jpeg_extension(extension)

    @Slot(str)
    def _sync_jpeg_extension(self, extension: str) -> None:
        index = self._jpeg_extension_combo.findData(extension)
        if index >= 0 and index != self._jpeg_extension_combo.currentIndex():
            self._jpeg_extension_combo.setCurrentIndex(index)

    @Slot(int)
    def _output_mode_changed(self, index: int) -> None:
        mode = self._output_mode_combo.itemData(index)
        if mode == "source":
            self._settings.set_output_directory(None)
            return

        if mode == "custom" and self._settings.output_directory is None:
            self._choose_output_directory()

    def _choose_output_directory(self) -> None:
        current_directory = self._settings.output_directory
        start_directory = str(current_directory or Path.home())
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            self._strings["settings_choose_directory_title"],
            start_directory,
        )
        if selected_directory:
            self._settings.set_output_directory(Path(selected_directory))
        elif current_directory is None:
            self._sync_output_directory(None)

    @Slot(object)
    def _sync_output_directory(self, directory: Path | None) -> None:
        mode = "custom" if directory is not None else "source"
        index = self._output_mode_combo.findData(mode)
        self._output_mode_combo.blockSignals(True)
        self._output_mode_combo.setCurrentIndex(index)
        self._output_mode_combo.blockSignals(False)

        self._custom_output_row.setVisible(directory is not None)
        self._output_path_label.setText("" if directory is None else str(directory))
