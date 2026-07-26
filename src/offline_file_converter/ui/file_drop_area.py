from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt, QThreadPool, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from offline_file_converter.models.selected_file import SelectedFile
from offline_file_converter.models.file_format import detect_file_format
from offline_file_converter.ui.file_card import CARD_MIME_TYPE, FileCard


CARD_MIN_WIDTH = 184
CARD_MAX_WIDTH = 248
CARD_GAP = 12
DROP_INDICATOR_WIDTH = 12
BASE_SUPPORTED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
}
OFFICE_SUPPORTED_SUFFIXES = {
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
}


class DropIndicator(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#168bd2"), 3, Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([2.2, 2.2])
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        x = self.width() // 2
        painter.drawLine(x, 7, x, self.height() - 7)

        cap_pen = QPen(QColor("#168bd2"), 3)
        cap_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(cap_pen)
        painter.drawLine(x - 4, 5, x + 4, 5)
        painter.drawLine(x - 4, self.height() - 5, x + 4, self.height() - 5)


class FileDropArea(QFrame):
    select_files_requested = Signal()
    files_changed = Signal(object)

    def __init__(
        self,
        strings: dict[str, str],
        office_support_enabled: bool = True,
    ) -> None:
        super().__init__()
        self._strings = strings
        self._supported_suffixes = set(BASE_SUPPORTED_SUFFIXES)
        if office_support_enabled:
            self._supported_suffixes.update(OFFICE_SUPPORTED_SUFFIXES)
        self._items: list[SelectedFile] = []
        self._cards: list[FileCard] = []
        self._known_paths: set[str] = set()
        self._current_columns = 0
        self._drag_insertion_index: int | None = None
        self._preview_pool = QThreadPool(self)
        self._preview_pool.setMaxThreadCount(3)
        self._input_message_timer = QTimer(self)
        self._input_message_timer.setSingleShot(True)
        self._input_message_timer.setInterval(3000)
        self._input_message_timer.timeout.connect(self._restore_hint)

        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(270)

        self._hint = QLabel(self._strings["drop_hint"])
        self._hint.setObjectName("dropHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setTextFormat(Qt.TextFormat.RichText)
        self._hint.setMinimumHeight(210)
        self._hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._cards_container = QWidget()
        self._cards_container.setObjectName("cardsContainer")
        self._cards_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        self._grid = QGridLayout(self._cards_container)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setHorizontalSpacing(CARD_GAP)
        self._grid.setVerticalSpacing(CARD_GAP)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._grid.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        self._drop_indicators = (
            DropIndicator(self._cards_container),
            DropIndicator(self._cards_container),
        )

        self._scroll = QScrollArea()
        self._scroll.setObjectName("fileScrollArea")
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setWidget(self._cards_container)
        self._scroll.setAcceptDrops(False)
        self._scroll.viewport().setAcceptDrops(False)
        self._scroll.viewport().installEventFilter(self)
        self._cards_container.installEventFilter(self)
        self._scroll.hide()
        self._scroll.verticalScrollBar().rangeChanged.connect(
            lambda _minimum, _maximum: QTimer.singleShot(0, self._reflow_cards)
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(4)
        layout.addWidget(self._hint)
        layout.addWidget(self._scroll, stretch=1)

    @property
    def ordered_files(self) -> tuple[SelectedFile, ...]:
        return tuple(self._items)

    @property
    def selected_format(self) -> str | None:
        return self._items[0].detected_format if self._items else None

    def add_files(self, paths: list[str]) -> None:
        last_card = None
        rejected_mixed_type = False
        selected_format = (
            self._items[0].detected_format if self._items else None
        )

        for raw_path in paths:
            path = Path(raw_path).expanduser().absolute()
            key = str(path)
            detected_format = detect_file_format(path)
            if (
                key in self._known_paths
                or not path.is_file()
                or path.suffix.lower() not in self._supported_suffixes
                or detected_format is None
            ):
                continue

            if selected_format is None:
                selected_format = detected_format
            elif detected_format != selected_format:
                rejected_mixed_type = True
                continue

            item = SelectedFile(
                path=path,
                order=len(self._items) + 1,
                detected_format=detected_format,
            )
            card = FileCard(item, self._strings, self._preview_pool)
            card.remove_requested.connect(self.remove_file)
            self._items.append(item)
            self._cards.append(card)
            self._known_paths.add(key)
            last_card = card

        if rejected_mixed_type:
            self._show_input_message(
                self._strings["mixed_file_types_not_allowed"]
            )

        if last_card is None:
            return

        if not rejected_mixed_type:
            self._restore_hint()
        self._hint.setMinimumHeight(52)
        self._hint.setMaximumHeight(52)
        self._hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._scroll.show()
        self._sync_order()
        self._reflow_cards()
        self.files_changed.emit(self.ordered_files)
        QTimer.singleShot(0, lambda: self._finish_adding(last_card))

    def remove_file(self, item_id: str) -> None:
        index = self._index_by_id(item_id)
        if index is None:
            return

        item = self._items.pop(index)
        card = self._cards.pop(index)
        self._known_paths.discard(str(item.path))
        card.deleteLater()

        self._sync_order()
        self._reflow_cards(force=True)

        if not self._cards:
            self._show_empty_state()
        self.files_changed.emit(self.ordered_files)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(CARD_MIME_TYPE):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        if self._paths_from_event(event):
            self._set_drag_active(True)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(CARD_MIME_TYPE):
            insertion_index = self._insertion_index(event.position().toPoint())
            self._show_drop_indicator(insertion_index)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        if self._paths_from_event(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_drag_active(False)
        self._hide_drop_indicator()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)

        if event.mimeData().hasFormat(CARD_MIME_TYPE):
            item_id = bytes(event.mimeData().data(CARD_MIME_TYPE)).decode("utf-8")
            insertion_index = self._insertion_index(event.position().toPoint())
            self._move_file(item_id, insertion_index)
            self._hide_drop_indicator()
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        paths = self._paths_from_event(event)
        if not paths:
            event.ignore()
            return

        self.add_files(paths)
        event.acceptProposedAction()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._cards:
            self._reflow_cards()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in (self._cards_container, self._scroll.viewport()):
            if event.type() == QEvent.Type.MouseButtonRelease:
                mouse_event = event
                if (
                    mouse_event.button() == Qt.MouseButton.LeftButton
                    and not self._position_is_over_card(
                        watched,
                        mouse_event.position().toPoint(),
                    )
                ):
                    self.select_files_requested.emit()
                    return True

        return super().eventFilter(watched, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._position_is_over_card(self, event.position().toPoint())
        ):
            self.select_files_requested.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _paths_from_event(
        self,
        event: QDragEnterEvent | QDragMoveEvent | QDropEvent,
    ) -> list[str]:
        paths = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if (
                path.is_file()
                and path.suffix.lower() in self._supported_suffixes
            ):
                paths.append(str(path))
        return paths

    def _position_is_over_card(self, source: QObject, point: QPoint) -> bool:
        if not isinstance(source, QWidget):
            return False

        container_point = self._cards_container.mapFrom(source, point)
        child = self._cards_container.childAt(container_point)
        while child is not None and child is not self._cards_container:
            if isinstance(child, FileCard):
                return True
            child = child.parentWidget()
        return False

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _finish_adding(self, last_card: FileCard) -> None:
        self._reflow_cards()
        self._scroll.ensureWidgetVisible(last_card, 12, 12)

    def _sync_order(self) -> None:
        total_files = len(self._items)
        for order, (item, card) in enumerate(zip(self._items, self._cards), start=1):
            item.order = order
            card.update_order(order, total_files)

    def _index_by_id(self, item_id: str) -> int | None:
        for index, item in enumerate(self._items):
            if item.id == item_id:
                return index
        return None

    def _move_file(self, item_id: str, insertion_index: int) -> None:
        source_index = self._index_by_id(item_id)
        if source_index is None:
            return

        item = self._items.pop(source_index)
        card = self._cards.pop(source_index)

        if insertion_index > source_index:
            insertion_index -= 1
        insertion_index = max(0, min(insertion_index, len(self._items)))

        self._items.insert(insertion_index, item)
        self._cards.insert(insertion_index, card)
        self._sync_order()
        self._reflow_cards(force=True)
        self.files_changed.emit(self.ordered_files)

    def _insertion_index(self, drop_position: QPoint) -> int:
        if not self._cards:
            return 0

        point = self._cards_container.mapFrom(self, drop_position)
        card = self._cards[0]
        step_x = card.width() + CARD_GAP
        step_y = card.height() + CARD_GAP
        column = max(0, (point.x() - 12 + step_x // 2) // step_x)
        row = max(0, (point.y() - 12) // step_y)
        return max(0, min(row * max(1, self._current_columns) + column, len(self._cards)))

    def _show_drop_indicator(self, insertion_index: int) -> None:
        if not self._cards:
            self._hide_drop_indicator()
            return

        self._drag_insertion_index = insertion_index
        self._position_drop_indicator()

    def _position_drop_indicator(self) -> None:
        if self._drag_insertion_index is None or not self._cards:
            return

        insertion_index = self._drag_insertion_index
        first_indicator, second_indicator = self._drop_indicators

        is_row_boundary = (
            0 < insertion_index < len(self._cards)
            and insertion_index % max(1, self._current_columns) == 0
        )

        if is_row_boundary:
            self._place_indicator(
                first_indicator,
                self._cards[insertion_index - 1],
                after_card=True,
            )
            self._place_indicator(
                second_indicator,
                self._cards[insertion_index],
                after_card=False,
            )
            return

        second_indicator.hide()
        if insertion_index < len(self._cards):
            reference_card = self._cards[insertion_index]
            self._place_indicator(first_indicator, reference_card, after_card=False)
        else:
            reference_card = self._cards[-1]
            self._place_indicator(first_indicator, reference_card, after_card=True)

    def _place_indicator(
        self,
        indicator: DropIndicator,
        reference_card: FileCard,
        *,
        after_card: bool,
    ) -> None:
        if after_card:
            marker_center = reference_card.geometry().right() + CARD_GAP // 2
        else:
            marker_center = reference_card.geometry().left() - CARD_GAP // 2

        indicator.setGeometry(
            marker_center - DROP_INDICATOR_WIDTH // 2,
            reference_card.geometry().top(),
            DROP_INDICATOR_WIDTH,
            reference_card.height(),
        )
        indicator.show()
        indicator.raise_()

    def _hide_drop_indicator(self) -> None:
        for indicator in self._drop_indicators:
            indicator.hide()
        self._drag_insertion_index = None

    def _show_empty_state(self) -> None:
        self._input_message_timer.stop()
        self._hint.setText(self._strings["drop_hint"])
        self._hint.setMinimumHeight(210)
        self._hint.setMaximumHeight(16777215)
        self._hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._scroll.hide()
        self._current_columns = 0
        self._hide_drop_indicator()

    def _show_input_message(self, message: str) -> None:
        self._input_message_timer.stop()
        self._hint.setText(message)
        self._input_message_timer.start()

    def _restore_hint(self) -> None:
        hint_key = "drop_hint_more" if self._items else "drop_hint"
        self._hint.setText(self._strings[hint_key])

    def _reflow_cards(self, force: bool = False) -> None:
        available_width = max(1, self._scroll.viewport().width() - 24)
        columns = max(1, (available_width + CARD_GAP) // (CARD_MIN_WIDTH + CARD_GAP))
        card_width = max(
            140,
            min(
                CARD_MAX_WIDTH,
                (available_width - CARD_GAP * (columns - 1)) // columns,
            ),
        )

        if not force and columns == self._current_columns and all(
            card.width() == card_width for card in self._cards
        ):
            return

        while self._grid.count():
            self._grid.takeAt(0)

        for index, card in enumerate(self._cards):
            card.setFixedWidth(card_width)
            self._grid.addWidget(card, index // columns, index % columns)

        self._current_columns = columns
        if any(indicator.isVisible() for indicator in self._drop_indicators):
            self._position_drop_indicator()
