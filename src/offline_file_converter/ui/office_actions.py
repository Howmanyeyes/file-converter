from pathlib import Path

from PySide6.QtCore import Slot

from offline_file_converter.conversion.office import (
    convert_office_files_to_jpeg,
    convert_office_files_to_pdf,
    convert_office_files_to_png,
)
from offline_file_converter.models.selected_file import SelectedFile
from offline_file_converter.ui.pdf_tools import PdfToolAction


class OfficeAction(PdfToolAction):
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
        self._office_paths: tuple[Path, ...] = ()
        self.setObjectName("officeConversionAction")
        self._button_shell.setObjectName("officeConversionButton")
        self._run_button.setObjectName("officeConversionRunButton")

    @Slot(object)
    def set_files(self, selected_files: tuple[SelectedFile, ...]) -> None:
        self._office_paths = tuple(
            item.path
            for item in selected_files
            if item.detected_format in {"word", "powerpoint"}
        )
        if not self._running:
            self._set_status(None)
        self.setVisible(bool(self._office_paths))
        self._update_availability()

    def _update_availability(self) -> None:
        self._run_button.setEnabled(
            bool(self._office_paths) and not self._running
        )


class OfficeToPdfAction(OfficeAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "office_to_pdf",
            "office_pdf_conversion_success",
            "office_pdf_conversion_failed",
        )

    def _activate(self) -> None:
        if not self._office_paths:
            return
        paths = self._office_paths
        output_directory = self._output_directory
        self._start_operation(
            lambda progress: convert_office_files_to_pdf(
                paths,
                output_directory,
                progress,
            )
        )


class OfficeToPngAction(OfficeAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "office_to_png",
            "office_png_conversion_success",
            "office_png_conversion_failed",
        )
        self._dpi = 150
        self._export_mode = "separate"

    @Slot(int)
    def set_dpi(self, dpi: int) -> None:
        self._dpi = dpi

    @Slot(str)
    def set_export_mode(self, export_mode: str) -> None:
        self._export_mode = export_mode

    def _activate(self) -> None:
        if not self._office_paths:
            return
        paths = self._office_paths
        dpi = self._dpi
        export_mode = self._export_mode
        output_directory = self._output_directory
        self._start_operation(
            lambda progress: convert_office_files_to_png(
                paths,
                dpi,
                output_directory,
                export_mode,
                progress,
            )
        )


class OfficeToJpegAction(OfficeAction):
    def __init__(self, strings: dict[str, str]) -> None:
        super().__init__(
            strings,
            "office_to_jpeg",
            "office_jpeg_conversion_success",
            "office_jpeg_conversion_failed",
        )
        self._dpi = 150
        self._export_mode = "separate"
        self._extension = "jpg"
        self._quality = 85
        self._update_button_text()

    @Slot(int)
    def set_dpi(self, dpi: int) -> None:
        self._dpi = dpi

    @Slot(str)
    def set_export_mode(self, export_mode: str) -> None:
        self._export_mode = export_mode

    @Slot(str)
    def set_extension(self, extension: str) -> None:
        if extension not in {"jpg", "jpeg"}:
            return
        self._extension = extension
        if not self._running:
            self._update_button_text()

    def _activate(self) -> None:
        if not self._office_paths:
            return
        paths = self._office_paths
        dpi = self._dpi
        quality = self._quality
        extension = self._extension
        export_mode = self._export_mode
        output_directory = self._output_directory
        self._start_operation(
            lambda progress: convert_office_files_to_jpeg(
                paths,
                dpi,
                quality,
                extension,
                output_directory,
                export_mode,
                progress,
            )
        )

    def _finish_operation(self) -> None:
        super()._finish_operation()
        self._update_button_text()

    def _update_button_text(self) -> None:
        self._run_button.setText(
            self._strings["office_to_jpeg"].format(
                extension=self._extension
            )
        )
