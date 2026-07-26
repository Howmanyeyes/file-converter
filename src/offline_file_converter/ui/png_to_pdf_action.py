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
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from offline_file_converter.conversion.png_to_pdf import convert_png_files_to_pdf
from offline_file_converter.models.selected_file import SelectedFile


def _load_icon(name: str) -> QIcon:
    resource = files("offline_file_converter.resources.icons").joinpath(name)
    return QIcon(str(resource))


class ConversionSignals(QObject):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)


class PngToPdfWorker(QRunnable):
    def __init__(
        self,
        paths: tuple[Path, ...],
        output_directory: Path | None,
    ) -> None:
        super().__init__()
        self._paths = paths
        self._output_directory = output_directory
        self.signals = ConversionSignals()

    @Slot()
    def run(self) -> None:
        try:
            outputs = convert_png_files_to_pdf(
                self._paths,
                self._output_directory,
                self.signals.progress.emit,
            )
        except Exception as error:
            details = str(error).strip() or error.__class__.__name__
            self.signals.failed.emit(details)
            return

        self.signals.succeeded.emit(outputs)


class PngToPdfAction(QFrame):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__()
        self._strings = strings
        self._png_paths: tuple[Path, ...] = ()
        self._output_directory: Path | None = None
        self._running = False
        self._worker: PngToPdfWorker | None = None

        self.setObjectName("pngToPdfAction")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._button_shell = QFrame()
        self._button_shell.setObjectName("pngToPdfButton")
        self._button_shell.setFixedSize(220, 46)

        button_layout = QHBoxLayout(self._button_shell)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self._run_button = QPushButton(self._strings["png_to_pdf"])
        self._run_button.setObjectName("pngToPdfRunButton")
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.clicked.connect(self._start_conversion)
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
        self._png_paths = tuple(
            item.path for item in selected_files if item.detected_format == "png"
        )
        if not self._running:
            self._set_status(None)
        self.setVisible(bool(self._png_paths))

    @Slot(object)
    def set_output_directory(self, directory: Path | None) -> None:
        self._output_directory = directory
        if not self._running:
            self._set_status(None)

    def _start_conversion(self) -> None:
        if self._running or not self._png_paths:
            return

        self._running = True
        self._set_status(None)
        self._run_button.setEnabled(False)
        self._run_button.setText(self._strings["conversion_starting"])

        self._worker = PngToPdfWorker(
            self._png_paths,
            self._output_directory,
        )
        self._worker.signals.progress.connect(self._update_progress)
        self._worker.signals.succeeded.connect(self._conversion_succeeded)
        self._worker.signals.failed.connect(self._conversion_failed)
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
    def _conversion_succeeded(self, outputs: list[Path]) -> None:
        tooltip = self._strings["png_pdf_conversion_success"]
        if outputs:
            tooltip = f"{tooltip}\n{outputs[0]}"
        self._finish_conversion()
        self._set_status("success", tooltip)

    @Slot(str)
    def _conversion_failed(self, details: str) -> None:
        tooltip = f"{self._strings['png_pdf_conversion_failed']}\n{details}"
        self._finish_conversion()
        self._set_status("failure", tooltip)

    def _finish_conversion(self) -> None:
        self._running = False
        self._worker = None
        self._run_button.setText(self._strings["png_to_pdf"])
        self._run_button.setEnabled(True)

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
