import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def find_libreoffice() -> Path | None:
    configured_path = os.environ.get("OFFLINE_FILE_CONVERTER_SOFFICE")
    if configured_path:
        candidate = Path(configured_path).expanduser()
        if candidate.is_file():
            return candidate

    executable_directory = Path(sys.executable).resolve().parent
    project_directory = Path(__file__).resolve().parents[2]
    candidates: list[Path] = []

    if sys.platform == "darwin":
        candidates.extend(
            (
                executable_directory.parent
                / "Frameworks/LibreOffice.app/Contents/MacOS/soffice",
                project_directory
                / "vendor/libreoffice/LibreOffice.app/Contents/MacOS/soffice",
                Path(
                    "/Applications/LibreOffice.app/Contents/MacOS/soffice"
                ),
            )
        )
    elif sys.platform == "win32":
        candidates.extend(
            (
                executable_directory / "libreoffice/program/soffice.exe",
                project_directory
                / "vendor/libreoffice/program/soffice.exe",
            )
        )
        for environment_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            program_files = os.environ.get(environment_name)
            if program_files:
                candidates.append(
                    Path(program_files) / "LibreOffice/program/soffice.exe"
                )

    bundled_or_installed = next(
        (candidate for candidate in candidates if candidate.is_file()),
        None,
    )
    if bundled_or_installed is not None:
        return bundled_or_installed

    for command_name in ("soffice", "libreoffice"):
        executable = shutil.which(command_name)
        if executable:
            return Path(executable)
    return None


def convert_office_document_to_pdf(
    source_path: Path,
    output_directory: Path,
) -> Path:
    libreoffice = find_libreoffice()
    if libreoffice is None:
        raise RuntimeError(
            "В приложении отсутствует компонент конвертации Word и "
            "PowerPoint. Переустановите Offline File Converter."
        )

    output_directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
        prefix="offline-file-converter-libreoffice-"
    ) as profile_directory:
        profile_uri = Path(profile_directory).as_uri()
        command = [
            str(libreoffice),
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_directory),
            str(source_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"LibreOffice не успел обработать {source_path.name}."
            ) from error

    expected_output = output_directory / f"{source_path.stem}.pdf"
    if result.returncode != 0 or not expected_output.is_file():
        details = (result.stderr or result.stdout).strip()
        message = f"LibreOffice не смог преобразовать {source_path.name}."
        if details:
            message = f"{message} {details}"
        raise RuntimeError(message)
    return expected_output
