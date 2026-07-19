import sys
import threading
from importlib.resources import files
from pathlib import Path

import pypdfium2 as pdfium
from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QMimeData,
    QObject,
    QPoint,
    QProcess,
    QRectF,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QDrag,
    QImage,
    QIcon,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from offline_file_converter.models.selected_file import SelectedFile


CARD_MIME_TYPE = "application/x-offline-file-converter-card"
PREVIEW_HEIGHT = 128
_PDFIUM_LOCK = threading.Lock()


def _load_icon(name: str) -> QIcon:
    resource = files("offline_file_converter.resources.icons").joinpath(name)
    return QIcon(str(resource))


def open_file(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_in_file_manager(path: Path) -> None:
    if sys.platform == "darwin":
        QProcess.startDetached("/usr/bin/open", ["-R", str(path)])
        return

    if sys.platform == "win32":
        QProcess.startDetached("explorer.exe", ["/select,", str(path)])
        return

    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


class PreviewSignals(QObject):
    ready = Signal(QImage)


class PreviewWorker(QRunnable):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.signals = PreviewSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.path.suffix.lower() == ".png":
                image = QImage(str(self.path))
            elif self.path.suffix.lower() == ".pdf":
                image = self._render_pdf_preview()
            else:
                image = QImage()
        except Exception:
            image = QImage()

        self.signals.ready.emit(image)

    def _render_pdf_preview(self) -> QImage:
        with _PDFIUM_LOCK:
            document = pdfium.PdfDocument(str(self.path))
            try:
                if len(document) == 0:
                    return QImage()

                page = document[0]
                try:
                    width, height = page.get_size()
                    scale = max(0.25, min(1.0, 220 / max(width, height)))
                    bitmap = page.render(scale=scale)
                    try:
                        pil_image = bitmap.to_pil().convert("RGBA")
                        pixels = pil_image.tobytes("raw", "RGBA")
                        return QImage(
                            pixels,
                            pil_image.width,
                            pil_image.height,
                            pil_image.width * 4,
                            QImage.Format.Format_RGBA8888,
                        ).copy()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
            finally:
                document.close()


class ClickablePreview(QLabel):
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._loading = True
        self._spinner_angle = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(45)
        self._spinner_timer.timeout.connect(self._advance_spinner)
        self._spinner_timer.start()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        if loading:
            self._spinner_timer.start()
        else:
            self._spinner_timer.stop()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._loading:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#007acc"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        diameter = 22
        spinner_rect = QRectF(
            (self.width() - diameter) / 2,
            (self.height() - diameter) / 2,
            diameter,
            diameter,
        )
        painter.drawArc(spinner_rect, self._spinner_angle * 16, 270 * 16)

    def _advance_spinner(self) -> None:
        self._spinner_angle = (self._spinner_angle - 18) % 360
        self.update()


class RemoveToolButton(QToolButton):
    def __init__(self, parent: QFrame) -> None:
        super().__init__(parent)
        self._normal_icon = _load_icon("close.svg")
        self._hover_icon = _load_icon("close-hover.svg")
        self.setIcon(self._normal_icon)

    def enterEvent(self, event: QEvent) -> None:
        self.setIcon(self._hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.setIcon(self._normal_icon)
        super().leaveEvent(event)


class FileCard(QFrame):
    remove_requested = Signal(str)

    def __init__(
        self,
        item: SelectedFile,
        strings: dict[str, str],
        preview_pool: QThreadPool,
    ) -> None:
        super().__init__()
        self.item = item
        self._strings = strings
        self._source_image = QImage()
        self._worker = PreviewWorker(item.path)
        self._drag_origin: QPoint | None = None
        self._drag_started_from_child = False

        self.setObjectName("fileCard")
        self.setFixedHeight(222)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._controls_overlay = QFrame(self)
        self._controls_overlay.setObjectName("fileControlsOverlay")

        controls_layout = QHBoxLayout(self._controls_overlay)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        self._remove_button = RemoveToolButton(self._controls_overlay)
        self._remove_button.setObjectName("removeFileButton")
        self._remove_button.setFixedSize(22, 22)
        self._remove_button.setIconSize(QSize(12, 12))
        self._remove_button.setAutoRaise(True)
        self._remove_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._remove_button.setToolTip(self._strings["remove_file"])
        self._remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_button.clicked.connect(lambda: self.remove_requested.emit(self.item.id))

        self._order_badge = QFrame(self._controls_overlay)
        self._order_badge.setObjectName("fileOrderBadge")
        self._order_badge.setFixedSize(22, 22)
        self._order_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        badge_layout = QHBoxLayout(self._order_badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)

        self._order_label = QLabel(self._order_badge)
        self._order_label.setObjectName("fileOrderText")
        self._order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._order_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        badge_layout.addWidget(self._order_label)

        controls_layout.addWidget(self._remove_button)
        controls_layout.addWidget(self._order_badge)

        self._preview = ClickablePreview()
        self._preview.setObjectName("filePreview")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedHeight(PREVIEW_HEIGHT)
        self._preview.clicked.connect(lambda: open_file(self.item.path))

        self._name_label = QLabel()
        self._name_label.setObjectName("fileName")
        self._name_label.setToolTip(item.path.name)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._path_button = QPushButton()
        self._path_button.setObjectName("filePathButton")
        self._path_button.setToolTip(str(item.path))
        self._path_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._path_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._path_button.clicked.connect(lambda: reveal_in_file_manager(self.item.path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(self._preview)
        layout.addWidget(self._name_label)
        layout.addWidget(self._path_button)

        self._preview.installEventFilter(self)
        self._path_button.installEventFilter(self)
        self._controls_overlay.installEventFilter(self)
        self._remove_button.installEventFilter(self)
        self._update_elided_texts()
        self._position_overlay_controls()
        self._worker.signals.ready.connect(self._set_preview)
        preview_pool.start(self._worker)

    def update_order(self, order: int, total_files: int) -> None:
        self.item.order = order
        self._order_label.setText(str(order))
        self._order_badge.setVisible(total_files > 1)
        self._position_overlay_controls()

    @Slot(QImage)
    def _set_preview(self, image: QImage) -> None:
        self._preview.set_loading(False)
        if image.isNull():
            self._preview.setText(self._strings["preview_unavailable"])
            return

        self._source_image = image
        self._update_preview_pixmap()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched not in (
            self._preview,
            self._path_button,
            self._controls_overlay,
            self._remove_button,
        ):
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.MouseButtonPress:
            mouse_event = event
            if mouse_event.button() == Qt.MouseButton.LeftButton:
                self._drag_origin = watched.mapTo(self, mouse_event.position().toPoint())
                self._drag_started_from_child = False

        elif event.type() == QEvent.Type.MouseMove and self._drag_origin is not None:
            mouse_event = event
            current_position = watched.mapTo(self, mouse_event.position().toPoint())
            if (
                mouse_event.buttons() & Qt.MouseButton.LeftButton
                and (current_position - self._drag_origin).manhattanLength()
                >= QApplication.startDragDistance()
            ):
                self._drag_started_from_child = True
                if isinstance(watched, QAbstractButton):
                    watched.setDown(False)
                self._start_drag(self._drag_origin)
                return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._drag_started_from_child:
                if isinstance(watched, QAbstractButton):
                    watched.setDown(False)
                self._drag_origin = None
                self._drag_started_from_child = False
                return True
            self._drag_origin = None

        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_origin is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and (event.position().toPoint() - self._drag_origin).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._start_drag(self._drag_origin)
            self._drag_origin = None
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_overlay_controls()
        self._update_elided_texts()
        self._update_preview_pixmap()

    def _start_drag(self, hot_spot: QPoint) -> None:
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(CARD_MIME_TYPE, QByteArray(self.item.id.encode("utf-8")))
        drag.setMimeData(mime_data)

        source_preview = self.grab()
        drag_preview = QPixmap(source_preview.size())
        drag_preview.setDevicePixelRatio(source_preview.devicePixelRatio())
        drag_preview.fill(Qt.GlobalColor.transparent)
        painter = QPainter(drag_preview)
        painter.setOpacity(0.38)
        painter.drawPixmap(0, 0, source_preview)
        painter.end()
        drag.setPixmap(drag_preview)
        drag.setHotSpot(hot_spot)

        self.setProperty("dragging", True)
        self.style().unpolish(self)
        self.style().polish(self)
        drag.exec(Qt.DropAction.MoveAction)
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def _position_overlay_controls(self) -> None:
        control_size = 22
        control_gap = 4
        overlay_width = control_size
        if self._order_badge.isVisible():
            overlay_width += control_gap + control_size

        self._controls_overlay.setGeometry(10, 10, overlay_width, control_size)
        self._controls_overlay.raise_()

    def _update_elided_texts(self) -> None:
        available_width = max(80, self.width() - 30)
        self._name_label.setText(
            self._name_label.fontMetrics().elidedText(
                self.item.path.name,
                Qt.TextElideMode.ElideMiddle,
                available_width,
            )
        )
        self._path_button.setText(
            self._path_button.fontMetrics().elidedText(
                str(self.item.path),
                Qt.TextElideMode.ElideMiddle,
                available_width,
            )
        )

    def _update_preview_pixmap(self) -> None:
        if self._source_image.isNull():
            return

        target_width = max(80, self.width() - 30)
        pixmap = QPixmap.fromImage(self._source_image).scaled(
            target_width,
            PREVIEW_HEIGHT - 8,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setText("")
        self._preview.setPixmap(pixmap)
