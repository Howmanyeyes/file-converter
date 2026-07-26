from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from offline_file_converter.conversion.pdf_compress import (
    compress_pdf_file,
    compress_pdf_with_high_quality,
)
from offline_file_converter.conversion.pdf_merge import merge_pdf_files
from offline_file_converter.conversion.pdf_split import split_pdf_file
from offline_file_converter.models.selected_file import SelectedFile


ProgressCallback = Callable[[int, int], None]
PdfOperation = Callable[[ProgressCallback], list[Path]]


def _load_icon(name: str) -> QIcon:
    resource = files("offline_file_converter.resources.icons").joinpath(name)
    return QIcon(str(resource))


class PdfToolSignals(QObject):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)


class PdfToolWorker(QRunnable):
    def __init__(self, operation: PdfOperation) -> None:
        super().__init__()
        self._operation = operation
        self.signals = PdfToolSignals()

    @Slot()
    def run(self) -> None:
        try:
            outputs = self._operation(self.signals.progress.emit)
        except Exception as error:
            details = str(error).strip() or error.__class__.__name__
            self.signals.failed.emit(details)
            return

        self.signals.succeeded.emit(outputs)


class PdfToolAction(QFrame):
    def __init__(
        self,
        strings: dict[str, str],
        button_text_key: str,
        success_text_key: str,
        failure_text_key: str,
    ) -> None:
        super().__init__()
        self._strings = strings
        self._button_text_key = button_text_key
        self._success_text_key = success_text_key
        self._failure_text_key = failure_text_key
        self._pdf_paths: tuple[Path, ...] = ()
        self._output_directory: Path | None = None
        self._running = False
        self._worker: PdfToolWorker | None = None

        self.setObjectName("pdfToolAction")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._button_shell = QFrame()
        self._button_shell.setObjectName("pdfToolButton")
        self._button_shell.setFixedSize(220, 46)

        button_layout = QHBoxLayout(self._button_shell)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self._run_button = QPushButton(self._strings[self._button_text_key])
        self._run_button.setObjectName("pdfToolRunButton")
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.clicked.connect(self._activate)
        button_layout.addWidget(self._run_button)

        self._status_badge = QFrame(self._button_shell)
        self._status_badge.setObjectName("conversionStatus")
        self._status_badge.setGeometry(84, 5, 52, 36)
        self._status_badge.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self._status_icon = QLabel(self._status_badge)
        self._status_icon.setObjectName("conversionStatusIcon")
        self._status_icon.setGeometry(0, 2, 52, 27)
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_icon.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self._status_countdown = QProgressBar(self._status_badge)
        self._status_countdown.setObjectName("conversionStatusCountdown")
        self._status_countdown.setGeometry(6, 31, 40, 3)
        self._status_countdown.setRange(0, 100)
        self._status_countdown.setTextVisible(False)
        self._status_countdown.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self._status_animation = QPropertyAnimation(
            self._status_countdown,
            b"value",
            self,
        )
        self._status_animation.setDuration(3000)
        self._status_animation.setStartValue(100)
        self._status_animation.setEndValue(0)
        self._status_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._status_animation.finished.connect(self._status_badge.hide)
        self._status_badge.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button_shell)
        self.hide()

    @Slot(object)
    def set_files(self, selected_files: tuple[SelectedFile, ...]) -> None:
        self._pdf_paths = tuple(
            item.path for item in selected_files if item.detected_format == "pdf"
        )
        if not self._running:
            self._set_status(None)
        self.setVisible(bool(self._pdf_paths))
        self._update_availability()

    @Slot(object)
    def set_output_directory(self, directory: Path | None) -> None:
        self._output_directory = directory
        if not self._running:
            self._set_status(None)

    def _activate(self) -> None:
        raise NotImplementedError

    def _update_availability(self) -> None:
        self._run_button.setEnabled(bool(self._pdf_paths) and not self._running)

    def _start_operation(self, operation: PdfOperation) -> None:
        if self._running:
            return

        self._running = True
        self._set_status(None)
        self._run_button.setEnabled(False)
        self._run_button.setText(self._strings["conversion_starting"])

        self._worker = PdfToolWorker(operation)
        self._worker.signals.progress.connect(self._update_progress)
        self._worker.signals.succeeded.connect(self._operation_succeeded)
        self._worker.signals.failed.connect(self._operation_failed)
        QThreadPool.globalInstance().start(self._worker)

    @Slot(int, int)
    def _update_progress(self, completed: int, total: int) -> None:
        self._run_button.setText(
            self._strings["conversion_progress"].format(
                completed=completed,
                total=total,
            )
        )

    @Slot(object)
    def _operation_succeeded(self, outputs: list[Path]) -> None:
        tooltip = self._strings[self._success_text_key].format(
            count=len(outputs)
        )
        if len(outputs) == 1:
            tooltip = f"{tooltip}\n{outputs[0]}"
        elif outputs:
            folders = sorted({str(path.parent) for path in outputs})
            tooltip = f"{tooltip}\n" + "\n".join(folders)
        self._finish_operation()
        self._set_status("success", tooltip)

    @Slot(str)
    def _operation_failed(self, details: str) -> None:
        tooltip = f"{self._strings[self._failure_text_key]}\n{details}"
        self._finish_operation()
        self._set_status("failure", tooltip)

    def _finish_operation(self) -> None:
        self._running = False
        self._worker = None
        self._run_button.setText(self._strings[self._button_text_key])
        self._update_availability()

    def _set_status(self, status: str | None, tooltip: str = "") -> None:
        self._status_animation.stop()
        if status is None:
            self._status_badge.hide()
            self._status_badge.setToolTip("")
            return

        icon_name = "status-success.svg" if status == "success" else "status-failure.svg"
        self._status_icon.setPixmap(_load_icon(icon_name).pixmap(QSize(22, 22)))
        self._status_badge.setProperty("status", status)
        self._status_badge.setToolTip(tooltip)
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)
        self._status_countdown.setValue(100)
        self._status_badge.show()
        self._status_badge.raise_()
        self._status_animation.start()


class PdfSplitAction(PdfToolAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "pdf_split",
            "pdf_split_success",
            "pdf_split_failed",
        )

    def _activate(self) -> None:
        if not self._pdf_paths:
            return

        dialog = PdfSplitDialog(self._pdf_paths, self._strings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        source_path = dialog.selected_path
        mode = dialog.split_mode
        range_specification = dialog.range_specification
        output_directory = self._output_directory
        self._start_operation(
            lambda progress: split_pdf_file(
                source_path,
                mode,
                range_specification,
                output_directory,
                progress,
            )
        )


class PdfMergeAction(PdfToolAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "pdf_merge",
            "pdf_merge_success",
            "pdf_merge_failed",
        )

    def _activate(self) -> None:
        if len(self._pdf_paths) < 2:
            return

        paths = self._pdf_paths
        output_directory = self._output_directory
        self._start_operation(
            lambda progress: merge_pdf_files(
                paths,
                output_directory,
                progress,
            )
        )

    def _update_availability(self) -> None:
        can_merge = len(self._pdf_paths) >= 2 and not self._running
        self._run_button.setEnabled(can_merge)
        self._run_button.setToolTip(
            "" if can_merge else self._strings["pdf_merge_requires_multiple"]
        )


class PdfCompressAction(PdfToolAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "pdf_compress",
            "pdf_compress_success",
            "pdf_compress_failed",
        )
        self._requested_target_size = 0
        self._minimum_quality = 65
        self._lossless_operation = False

    @Slot(int)
    def set_minimum_quality(self, quality: int) -> None:
        self._minimum_quality = quality
        if not self._running:
            self._set_status(None)

    def _activate(self) -> None:
        if not self._pdf_paths:
            return

        dialog = PdfCompressDialog(self._pdf_paths, self._strings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        source_path = dialog.selected_path
        self._lossless_operation = dialog.lossless
        output_directory = self._output_directory
        if self._lossless_operation:
            self._start_operation(
                lambda progress: compress_pdf_with_high_quality(
                    source_path,
                    output_directory,
                    progress,
                )
            )
            return

        target_size_bytes = dialog.target_size_bytes
        self._requested_target_size = target_size_bytes
        minimum_quality = self._minimum_quality
        self._start_operation(
            lambda progress: compress_pdf_file(
                source_path,
                target_size_bytes,
                minimum_quality,
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
            tooltip = self._strings["pdf_compress_minimum_success"].format(
                size=_format_size(outputs[0].stat().st_size)
            )
            tooltip = f"{tooltip}\n{outputs[0]}"
            self._finish_operation()
            self._set_status("success", tooltip)
            return
        super()._operation_succeeded(outputs)


class PdfSourceDialog(QDialog):
    def __init__(
        self,
        paths: tuple[Path, ...],
        strings: dict[str, str],
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._paths = paths
        self._strings = strings
        self.setObjectName("pdfToolDialog")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._source_combo = QComboBox()
        self._source_combo.setObjectName("pdfToolCombo")
        self._source_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        for path in self._paths:
            self._source_combo.addItem(path.name, str(path))
            self._source_combo.setItemData(
                self._source_combo.count() - 1,
                str(path),
                Qt.ItemDataRole.ToolTipRole,
            )

    @property
    def selected_path(self) -> Path:
        return Path(str(self._source_combo.currentData()))

    def _add_title(
        self,
        layout: QVBoxLayout,
        title_text: str,
        description_text: str,
    ) -> None:
        title = QLabel(title_text)
        title.setObjectName("pdfToolTitle")

        description = QLabel(description_text)
        description.setObjectName("pdfToolDescription")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)

    def _add_field_label(
        self,
        layout: QVBoxLayout,
        text: str,
    ) -> QLabel:
        label = QLabel(text)
        label.setObjectName("pdfToolFieldLabel")
        layout.addWidget(label)
        return label

    def _create_buttons(
        self,
        confirm_text: str,
        lossless_text: str | None = None,
    ) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.setObjectName("pdfToolButtons")
        confirm_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        confirm_button.setObjectName("pdfToolConfirmButton")
        cancel_button.setObjectName("pdfToolCancelButton")
        confirm_button.setText(confirm_text)
        cancel_button.setText(self._strings["cancel"])
        if lossless_text is not None:
            lossless_button = buttons.addButton(
                lossless_text,
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            lossless_button.setObjectName("pdfToolLosslessButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        return buttons


class PdfSplitDialog(PdfSourceDialog):
    def __init__(
        self,
        paths: tuple[Path, ...],
        strings: dict[str, str],
        parent: QWidget,
    ) -> None:
        super().__init__(paths, strings, parent)
        self.setWindowTitle(self._strings["pdf_split_dialog_title"])
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)
        self._add_title(
            layout,
            self._strings["pdf_split_dialog_title"],
            self._strings["pdf_split_dialog_description"],
        )

        self._add_field_label(layout, self._strings["pdf_source_file"])
        layout.addWidget(self._source_combo)

        self._add_field_label(layout, self._strings["pdf_split_mode"])
        self._mode_combo = QComboBox()
        self._mode_combo.setObjectName("pdfToolCombo")
        self._mode_combo.addItem(
            self._strings["pdf_split_every_page"],
            "pages",
        )
        self._mode_combo.addItem(
            self._strings["pdf_split_by_ranges"],
            "ranges",
        )
        layout.addWidget(self._mode_combo)

        self._range_container = QWidget()
        self._range_container.setObjectName("pdfToolFieldContainer")
        range_layout = QVBoxLayout(self._range_container)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(6)

        range_label = QLabel(self._strings["pdf_split_ranges"])
        range_label.setObjectName("pdfToolFieldLabel")
        self._range_input = QLineEdit()
        self._range_input.setObjectName("pdfToolLineEdit")
        self._range_input.setPlaceholderText(
            self._strings["pdf_split_ranges_placeholder"]
        )
        range_hint = QLabel(self._strings["pdf_split_ranges_hint"])
        range_hint.setObjectName("pdfToolHint")
        range_hint.setWordWrap(True)
        range_layout.addWidget(range_label)
        range_layout.addWidget(self._range_input)
        range_layout.addWidget(range_hint)
        layout.addWidget(self._range_container)

        self._error_label = QLabel()
        self._error_label.setObjectName("pdfToolError")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._error_label)
        layout.addStretch(1)
        layout.addWidget(
            self._create_buttons(self._strings["pdf_split_start"])
        )

        self._mode_combo.currentIndexChanged.connect(
            self._update_range_visibility
        )
        self._update_range_visibility()

    @property
    def split_mode(self) -> str:
        return str(self._mode_combo.currentData())

    @property
    def range_specification(self) -> str:
        return self._range_input.text().strip()

    def accept(self) -> None:
        if self.split_mode == "ranges":
            tokens = [
                token.strip()
                for token in self.range_specification.split(",")
                if token.strip()
            ]
            if len(tokens) < 2:
                self._error_label.setText(
                    self._strings["pdf_split_ranges_error"]
                )
                self._error_label.show()
                return
        super().accept()

    def _update_range_visibility(self) -> None:
        self._range_container.setVisible(self.split_mode == "ranges")
        self._error_label.hide()
        self.adjustSize()


class PdfCompressDialog(PdfSourceDialog):
    def __init__(
        self,
        paths: tuple[Path, ...],
        strings: dict[str, str],
        parent: QWidget,
    ) -> None:
        super().__init__(paths, strings, parent)
        self._lossless = False
        self.setWindowTitle(self._strings["pdf_compress_dialog_title"])
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)
        self._add_title(
            layout,
            self._strings["pdf_compress_dialog_title"],
            self._strings["pdf_compress_dialog_description"],
        )

        self._add_field_label(layout, self._strings["pdf_source_file"])
        layout.addWidget(self._source_combo)

        self._source_size_label = QLabel()
        self._source_size_label.setObjectName("pdfToolHint")
        layout.addWidget(self._source_size_label)

        self._add_field_label(layout, self._strings["pdf_target_size"])
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

        warning = QLabel(self._strings["pdf_compress_quality_warning"])
        warning.setObjectName("pdfToolHint")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        layout.addStretch(1)
        layout.addWidget(
            self._create_buttons(
                self._strings["pdf_compress_start"],
                self._strings["pdf_compress_high_quality"],
            )
        )
        lossless_button = self.findChild(
            QPushButton,
            "pdfToolLosslessButton",
        )
        if lossless_button is not None:
            lossless_button.clicked.connect(self._accept_lossless)

        self._source_combo.currentIndexChanged.connect(
            self._sync_source_information
        )
        self._sync_source_information()

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
            self._strings["pdf_source_size"].format(
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
