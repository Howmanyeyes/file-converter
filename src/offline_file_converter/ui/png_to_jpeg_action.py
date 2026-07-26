from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from offline_file_converter.conversion.png_to_jpeg import convert_png_files_to_jpeg
from offline_file_converter.models.selected_file import SelectedFile


def _load_icon(name: str) -> QIcon:
    resource = files("offline_file_converter.resources.icons").joinpath(name)
    return QIcon(str(resource))


class ConversionSignals(QObject):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)


class PngToJpegWorker(QRunnable):
    def __init__(
        self,
        paths: tuple[Path, ...],
        quality: int,
        extension: str,
        output_directory: Path | None,
    ) -> None:
        super().__init__()
        self._paths = paths
        self._quality = quality
        self._extension = extension
        self._output_directory = output_directory
        self.signals = ConversionSignals()

    @Slot()
    def run(self) -> None:
        try:
            outputs = convert_png_files_to_jpeg(
                self._paths,
                self._quality,
                self._extension,
                self._output_directory,
                self.signals.progress.emit,
            )
        except Exception as error:
            details = str(error).strip() or error.__class__.__name__
            self.signals.failed.emit(details)
            return

        self.signals.succeeded.emit(outputs)


class PngToJpegAction(QFrame):
    extension_selected = Signal(str)

    QUALITY_OPTIONS = (
        (95, "jpeg_compression_minimal"),
        (85, "jpeg_compression_medium"),
        (70, "jpeg_compression_strong"),
    )

    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__()
        self._strings = strings
        self._png_paths: tuple[Path, ...] = ()
        self._quality = 85
        self._extension = "jpg"
        self._output_directory: Path | None = None
        self._running = False
        self._worker: PngToJpegWorker | None = None

        self.setObjectName("pngToJpegAction")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._button_shell = QFrame()
        self._button_shell.setObjectName("pngToJpegButton")
        self._button_shell.setFixedSize(220, 46)

        button_layout = QHBoxLayout(self._button_shell)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)

        self._run_button = QPushButton(self._button_text())
        self._run_button.setObjectName("pngToJpegRunButton")
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.clicked.connect(self._start_conversion)

        self._options_button = QPushButton()
        self._options_button.setObjectName("pngToJpegOptionsButton")
        self._options_button.setFixedWidth(42)
        self._options_button.setIcon(_load_icon("chevron-down.svg"))
        self._options_button.setIconSize(QSize(14, 14))
        self._options_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._options_button.clicked.connect(self._show_options_menu)

        button_layout.addWidget(self._run_button, stretch=1)
        button_layout.addWidget(self._options_button)

        self._options_menu = QMenu(self)
        self._options_menu.setObjectName("jpegOptionsMenu")

        self._quality_actions = QActionGroup(self)
        self._quality_actions.setExclusive(True)
        self._options_menu.addSection(self._strings["jpeg_compression"])
        for quality, string_key in self.QUALITY_OPTIONS:
            action = QAction(self._strings[string_key], self)
            action.setCheckable(True)
            action.setChecked(quality == self._quality)
            action.triggered.connect(
                lambda _checked=False, selected_quality=quality: self._set_quality(
                    selected_quality
                )
            )
            self._quality_actions.addAction(action)
            self._options_menu.addAction(action)

        self._options_menu.addSeparator()
        self._options_menu.addSection(self._strings["jpeg_extension"])
        self._extension_actions = QActionGroup(self)
        self._extension_actions.setExclusive(True)
        for extension in ("jpg", "jpeg"):
            action = QAction(f".{extension}", self)
            action.setData(extension)
            action.setCheckable(True)
            action.setChecked(extension == self._extension)
            action.triggered.connect(
                lambda _checked=False, selected_extension=extension: self._set_extension(
                    selected_extension
                )
            )
            self._extension_actions.addAction(action)
            self._options_menu.addAction(action)

        self._update_options_tooltip()

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

    def _button_text(self) -> str:
        return self._strings["png_to_jpeg"].format(extension=self._extension)

    def _set_quality(self, quality: int) -> None:
        self._quality = quality
        self._update_options_tooltip()
        self._set_status(None)

    def _set_extension(self, extension: str) -> None:
        self.set_extension(extension)
        self.extension_selected.emit(extension)

    @Slot(str)
    def set_extension(self, extension: str) -> None:
        if extension not in {"jpg", "jpeg"}:
            return
        self._extension = extension
        for action in self._extension_actions.actions():
            action.setChecked(action.data() == extension)
        if not self._running:
            self._run_button.setText(self._button_text())
        self._update_options_tooltip()
        if not self._running:
            self._set_status(None)

    def _update_options_tooltip(self) -> None:
        quality_name = next(
            self._strings[string_key]
            for quality, string_key in self.QUALITY_OPTIONS
            if quality == self._quality
        )
        self._options_button.setToolTip(
            self._strings["jpeg_options_tooltip"].format(
                quality=quality_name,
                extension=f".{self._extension}",
            )
        )

    def _show_options_menu(self) -> None:
        bottom_right = self._options_button.mapToGlobal(
            QPoint(self._options_button.width(), self._options_button.height())
        )
        menu_width = self._options_menu.sizeHint().width()
        self._options_menu.exec(
            QPoint(bottom_right.x() - menu_width, bottom_right.y())
        )

    def _start_conversion(self) -> None:
        if self._running or not self._png_paths:
            return

        self._running = True
        self._set_status(None)
        self._run_button.setEnabled(False)
        self._options_button.setEnabled(False)
        self._run_button.setText(self._strings["conversion_starting"])

        self._worker = PngToJpegWorker(
            self._png_paths,
            self._quality,
            self._extension,
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
        folders = sorted({str(output.parent) for output in outputs})
        tooltip = self._strings["png_jpeg_conversion_success"].format(
            count=len(outputs)
        )
        if folders:
            tooltip = f"{tooltip}\n" + "\n".join(folders)
        self._finish_conversion()
        self._set_status("success", tooltip)

    @Slot(str)
    def _conversion_failed(self, details: str) -> None:
        tooltip = f"{self._strings['png_jpeg_conversion_failed']}\n{details}"
        self._finish_conversion()
        self._set_status("failure", tooltip)

    def _finish_conversion(self) -> None:
        self._running = False
        self._worker = None
        self._run_button.setText(self._button_text())
        self._run_button.setEnabled(True)
        self._options_button.setEnabled(True)

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
