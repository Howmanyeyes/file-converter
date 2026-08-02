from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader, PdfWriter


ProgressCallback = Callable[[int, int], None]


def split_pdf_file(
    path: Path,
    mode: str,
    range_specification: str,
    output_directory: Path | None,
    progress_callback: ProgressCallback,
) -> list[Path]:
    if mode not in {"pages", "ranges"}:
        raise ValueError("Неизвестный режим разделения PDF.")

    created_outputs: list[Path] = []
    temporary_outputs: list[Path] = []

    try:
        source_pdf = PdfReader(str(path))
        page_count = len(source_pdf.pages)
        if page_count < 2:
            raise ValueError("В PDF должна быть минимум две страницы.")

        page_groups = (
            [(page_index,) for page_index in range(page_count)]
            if mode == "pages"
            else _parse_page_groups(range_specification, page_count)
        )
        if len(page_groups) < 2:
            raise ValueError(
                "Укажите минимум две части, разделяя диапазоны запятыми."
            )

        destination = output_directory or path.parent
        output_paths = _available_output_paths(
            destination,
            path.stem,
            len(page_groups),
        )

        for part_index, (page_group, output_path) in enumerate(
            zip(page_groups, output_paths),
            start=1,
        ):
            temporary_path = output_path.with_name(
                f".{output_path.name}.{uuid4().hex}.tmp"
            )
            temporary_outputs.append(temporary_path)

            part_pdf = PdfWriter()
            for page_index in page_group:
                part_pdf.add_page(source_pdf.pages[page_index])
            part_pdf.compress_identical_objects(
                remove_duplicates=True,
                remove_unreferenced=True,
            )
            with temporary_path.open("wb") as output_file:
                part_pdf.write(output_file)

            temporary_path.replace(output_path)
            temporary_outputs.remove(temporary_path)
            created_outputs.append(output_path)
            progress_callback(part_index, len(page_groups))

        return created_outputs
    except Exception:
        for temporary_path in temporary_outputs:
            temporary_path.unlink(missing_ok=True)
        for output_path in created_outputs:
            output_path.unlink(missing_ok=True)
        raise


def _parse_page_groups(
    specification: str,
    page_count: int,
) -> list[tuple[int, ...]]:
    tokens = [token.strip() for token in specification.split(",")]
    if not tokens or any(not token for token in tokens):
        raise ValueError(
            "Введите диапазоны через запятую, например: 1-3, 4-7, 8."
        )

    groups: list[tuple[int, ...]] = []
    for token in tokens:
        if "-" in token:
            boundaries = [part.strip() for part in token.split("-")]
            if len(boundaries) != 2:
                raise ValueError(f"Некорректный диапазон: {token}.")
            start = _parse_page_number(boundaries[0], page_count)
            end = _parse_page_number(boundaries[1], page_count)
            if start > end:
                raise ValueError(
                    f"Начало диапазона больше конца: {token}."
                )
            groups.append(tuple(range(start - 1, end)))
            continue

        page_number = _parse_page_number(token, page_count)
        groups.append((page_number - 1,))

    return groups


def _parse_page_number(value: str, page_count: int) -> int:
    try:
        page_number = int(value)
    except ValueError as error:
        raise ValueError(f"Некорректный номер страницы: {value}.") from error

    if not 1 <= page_number <= page_count:
        raise ValueError(
            f"Страница {page_number} вне диапазона 1–{page_count}."
        )
    return page_number


def _available_output_paths(
    destination: Path,
    source_stem: str,
    part_count: int,
) -> list[Path]:
    number_width = max(3, len(str(part_count)))
    version = 1

    while True:
        collision_suffix = "" if version == 1 else f"_{version}"
        candidates = [
            destination
            / (
                f"{source_stem}_part_{part_number:0{number_width}d}"
                f"{collision_suffix}.pdf"
            )
            for part_number in range(1, part_count + 1)
        ]
        if not any(candidate.exists() for candidate in candidates):
            return candidates
        version += 1
