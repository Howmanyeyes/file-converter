from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from offline_file_converter.conversion.png_compress import (
    compress_png_file,
    compress_png_losslessly,
)
from offline_file_converter.conversion.png_merge import merge_png_files
from offline_file_converter.models.selected_file import SelectedFile
from offline_file_converter.ui.pdf_tools import PdfToolAction


class PngToolAction(PdfToolAction):
    def __init__(
        self,
        strings: dict[str, str],
        button_text_key: str,
        success_text_key: str,
        failure_text_key: str,
    ) -> None:
        super().__init__(
            strings,
            button_text_key,
            success_text_key,
            failure_text_key,
        )
        self._png_paths: tuple[Path, ...] = ()
        self.setObjectName("pngToolAction")
        self._button_shell.setObjectName("pngToolButton")
        self._run_button.setObjectName("pngToolRunButton")

    @Slot(object)
    def set_files(self, selected_files: tuple[SelectedFile, ...]) -> None:
        self._png_paths = tuple(
            item.path for item in selected_files if item.detected_format == "png"
        )
        if not self._running:
            self._set_status(None)
        self.setVisible(bool(self._png_paths))
        self._update_availability()

    def _update_availability(self) -> None:
        self._run_button.setEnabled(bool(self._png_paths) and not self._running)


class PngMergeAction(PngToolAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "png_merge",
            "png_merge_success",
            "png_merge_failed",
        )

    def _activate(self) -> None:
        if len(self._png_paths) < 2:
            return

        paths = self._png_paths
        output_directory = self._output_directory
        self._start_operation(
            lambda progress: merge_png_files(
                paths,
                output_directory,
                progress,
            )
        )

    def _update_availability(self) -> None:
        can_merge = len(self._png_paths) >= 2 and not self._running
        self._run_button.setEnabled(can_merge)
        self._run_button.setToolTip(
            "" if can_merge else self._strings["png_merge_requires_multiple"]
        )


class PngCompressAction(PngToolAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "png_compress",
            "png_compress_success",
            "png_compress_failed",
        )
        self._requested_target_size = 0
        self._lossless_operation = False

    def _activate(self) -> None:
        if not self._png_paths:
            return

        dialog = PngCompressDialog(self._png_paths, self._strings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        source_path = dialog.selected_path
        self._lossless_operation = dialog.lossless
        output_directory = self._output_directory
        if self._lossless_operation:
            self._start_operation(
                lambda progress: compress_png_losslessly(
                    source_path,
                    output_directory,
                    progress,
                )
            )
            return

        target_size_bytes = dialog.target_size_bytes
        self._requested_target_size = target_size_bytes
        self._start_operation(
            lambda progress: compress_png_file(
                source_path,
                target_size_bytes,
                output_directory,
                progress,
            )
        )

    @Slot(object)
    def _operation_succeeded(self, outputs: list[Path]) -> None:
        if (
            not self._lossless_operation
            and outputs
            and outputs[0].stat().st_size > self._requested_target_size
        ):
            tooltip = self._strings["png_compress_minimum_success"].format(
                size=_format_size(outputs[0].stat().st_size)
            )
            tooltip = f"{tooltip}\n{outputs[0]}"
            self._finish_operation()
            self._set_status("success", tooltip)
            return
        super()._operation_succeeded(outputs)


class PngCompressDialog(QDialog):
    def __init__(
        self,
        paths: tuple[Path, ...],
        strings: dict[str, str],
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._strings = strings
        self._lossless = False
        self.setObjectName("pdfToolDialog")
        self.setWindowTitle(self._strings["png_compress_dialog_title"])
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(520)

        self._source_combo = QComboBox()
        self._source_combo.setObjectName("pdfToolCombo")
        self._source_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        for path in paths:
            self._source_combo.addItem(path.name, str(path))
            self._source_combo.setItemData(
                self._source_combo.count() - 1,
                str(path),
                Qt.ItemDataRole.ToolTipRole,
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        title = QLabel(self._strings["png_compress_dialog_title"])
        title.setObjectName("pdfToolTitle")
        description = QLabel(
            self._strings["png_compress_dialog_description"]
        )
        description.setObjectName("pdfToolDescription")
        description.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(description)

        source_label = QLabel(self._strings["png_source_file"])
        source_label.setObjectName("pdfToolFieldLabel")
        layout.addWidget(source_label)
        layout.addWidget(self._source_combo)

        self._source_size_label = QLabel()
        self._source_size_label.setObjectName("pdfToolHint")
        layout.addWidget(self._source_size_label)

        target_label = QLabel(self._strings["png_target_size"])
        target_label.setObjectName("pdfToolFieldLabel")
        layout.addWidget(target_label)

        target_row = QWidget()
        target_row.setObjectName("pdfToolFieldContainer")
        target_layout = QHBoxLayout(target_row)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(8)

        self._target_size_input = QDoubleSpinBox()
        self._target_size_input.setObjectName("pdfToolSizeInput")
        self._target_size_input.setDecimals(2)
        self._target_size_input.setRange(0.01, 999999.0)
        self._target_size_input.setSingleStep(0.1)
        self._target_size_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._unit_combo = QComboBox()
        self._unit_combo.setObjectName("pdfToolUnitCombo")
        self._unit_combo.addItem(self._strings["size_kb"], 1024)
        self._unit_combo.addItem(self._strings["size_mb"], 1024 * 1024)
        self._unit_combo.setFixedWidth(90)

        target_layout.addWidget(self._target_size_input, stretch=1)
        target_layout.addWidget(self._unit_combo)
        layout.addWidget(target_row)

        warning = QLabel(self._strings["png_compress_quality_warning"])
        warning.setObjectName("pdfToolHint")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.setObjectName("pdfToolButtons")
        confirm_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        confirm_button.setObjectName("pdfToolConfirmButton")
        cancel_button.setObjectName("pdfToolCancelButton")
        lossless_button = buttons.addButton(
            self._strings["png_compress_losslessly"],
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        lossless_button.setObjectName("pdfToolLosslessButton")
        confirm_button.setText(self._strings["png_compress_start"])
        cancel_button.setText(self._strings["cancel"])
        lossless_button.clicked.connect(self._accept_lossless)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._source_combo.currentIndexChanged.connect(
            self._sync_source_information
        )
        self._sync_source_information()

    @property
    def selected_path(self) -> Path:
        return Path(str(self._source_combo.currentData()))

    @property
    def target_size_bytes(self) -> int:
        multiplier = int(self._unit_combo.currentData())
        return max(1, round(self._target_size_input.value() * multiplier))

    @property
    def lossless(self) -> bool:
        return self._lossless

    def _accept_lossless(self) -> None:
        self._lossless = True
        self.accept()

    def _sync_source_information(self) -> None:
        source_size = self.selected_path.stat().st_size
        self._source_size_label.setText(
            self._strings["png_source_size"].format(
                size=_format_size(source_size)
            )
        )

        target_size = max(1, round(source_size * 0.7))
        if target_size >= 1024 * 1024:
            self._unit_combo.setCurrentIndex(1)
            self._target_size_input.setValue(
                target_size / (1024 * 1024)
            )
        else:
            self._unit_combo.setCurrentIndex(0)
            self._target_size_input.setValue(target_size / 1024)


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} МБ"
    return f"{size_bytes / 1024:.0f} КБ"
