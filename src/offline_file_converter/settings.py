from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal


class AppSettings(QObject):
    pdf_dpi_changed = Signal(int)
    pdf_export_mode_changed = Signal(str)
    pdf_min_compression_quality_changed = Signal(int)
    jpeg_extension_changed = Signal(str)
    output_directory_changed = Signal(object)

    PDF_DPI_KEY = "conversion/pdf_dpi"
    PDF_EXPORT_MODE_KEY = "conversion/pdf_export_mode"
    PDF_MIN_COMPRESSION_QUALITY_KEY = (
        "conversion/pdf_min_compression_quality"
    )
    JPEG_EXTENSION_KEY = "conversion/jpeg_extension"
    OUTPUT_DIRECTORY_KEY = "conversion/output_directory"
    PDF_DPI_OPTIONS = (72, 96, 150, 200, 300, 600)
    DEFAULT_PDF_DPI = 150
    PDF_EXPORT_MODE_OPTIONS = ("single", "separate")
    DEFAULT_PDF_EXPORT_MODE = "separate"
    PDF_MIN_COMPRESSION_QUALITY_OPTIONS = (
        90,
        85,
        80,
        75,
        70,
        65,
        60,
        55,
        50,
        45,
        40,
        35,
        30,
    )
    DEFAULT_PDF_MIN_COMPRESSION_QUALITY = 65
    JPEG_EXTENSION_OPTIONS = ("jpg", "jpeg")
    DEFAULT_JPEG_EXTENSION = "jpg"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._storage = QSettings(
            "Offline File Converter",
            "Offline File Converter",
        )

    @property
    def pdf_dpi(self) -> int:
        stored_value = self._storage.value(
            self.PDF_DPI_KEY,
            self.DEFAULT_PDF_DPI,
        )
        try:
            dpi = int(stored_value)
        except (TypeError, ValueError):
            return self.DEFAULT_PDF_DPI

        if dpi not in self.PDF_DPI_OPTIONS:
            return self.DEFAULT_PDF_DPI
        return dpi

    def set_pdf_dpi(self, dpi: int) -> None:
        if dpi not in self.PDF_DPI_OPTIONS or dpi == self.pdf_dpi:
            return

        self._storage.setValue(self.PDF_DPI_KEY, dpi)
        self._storage.sync()
        self.pdf_dpi_changed.emit(dpi)

    @property
    def pdf_export_mode(self) -> str:
        stored_value = str(
            self._storage.value(
                self.PDF_EXPORT_MODE_KEY,
                self.DEFAULT_PDF_EXPORT_MODE,
            )
        )
        if stored_value not in self.PDF_EXPORT_MODE_OPTIONS:
            return self.DEFAULT_PDF_EXPORT_MODE
        return stored_value

    def set_pdf_export_mode(self, mode: str) -> None:
        if (
            mode not in self.PDF_EXPORT_MODE_OPTIONS
            or mode == self.pdf_export_mode
        ):
            return

        self._storage.setValue(self.PDF_EXPORT_MODE_KEY, mode)
        self._storage.sync()
        self.pdf_export_mode_changed.emit(mode)

    @property
    def pdf_min_compression_quality(self) -> int:
        stored_value = self._storage.value(
            self.PDF_MIN_COMPRESSION_QUALITY_KEY,
            self.DEFAULT_PDF_MIN_COMPRESSION_QUALITY,
        )
        try:
            quality = int(stored_value)
        except (TypeError, ValueError):
            return self.DEFAULT_PDF_MIN_COMPRESSION_QUALITY

        if quality not in self.PDF_MIN_COMPRESSION_QUALITY_OPTIONS:
            return self.DEFAULT_PDF_MIN_COMPRESSION_QUALITY
        return quality

    def set_pdf_min_compression_quality(self, quality: int) -> None:
        if (
            quality not in self.PDF_MIN_COMPRESSION_QUALITY_OPTIONS
            or quality == self.pdf_min_compression_quality
        ):
            return

        self._storage.setValue(
            self.PDF_MIN_COMPRESSION_QUALITY_KEY,
            quality,
        )
        self._storage.sync()
        self.pdf_min_compression_quality_changed.emit(quality)

    @property
    def jpeg_extension(self) -> str:
        extension = str(
            self._storage.value(
                self.JPEG_EXTENSION_KEY,
                self.DEFAULT_JPEG_EXTENSION,
            )
        ).lower()
        if extension not in self.JPEG_EXTENSION_OPTIONS:
            return self.DEFAULT_JPEG_EXTENSION
        return extension

    def set_jpeg_extension(self, extension: str) -> None:
        normalized_extension = extension.lower()
        if (
            normalized_extension not in self.JPEG_EXTENSION_OPTIONS
            or normalized_extension == self.jpeg_extension
        ):
            return
        self._storage.setValue(
            self.JPEG_EXTENSION_KEY,
            normalized_extension,
        )
        self._storage.sync()
        self.jpeg_extension_changed.emit(normalized_extension)

    @property
    def output_directory(self) -> Path | None:
        stored_value = self._storage.value(self.OUTPUT_DIRECTORY_KEY, "")
        if not stored_value:
            return None
        return Path(str(stored_value))

    def set_output_directory(self, directory: Path | None) -> None:
        normalized_directory = (
            None if directory is None else directory.expanduser().absolute()
        )
        if normalized_directory == self.output_directory:
            return

        if normalized_directory is None:
            self._storage.remove(self.OUTPUT_DIRECTORY_KEY)
        else:
            self._storage.setValue(
                self.OUTPUT_DIRECTORY_KEY,
                str(normalized_directory),
            )
        self._storage.sync()
        self.output_directory_changed.emit(normalized_directory)
