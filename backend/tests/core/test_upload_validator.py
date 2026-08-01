"""Verification tests for `app.core.upload.UploadValidator` (Phase 4.2).

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/core/test_upload_validator.py
"""

import asyncio
import io

from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.core.upload import (
    CorruptedImageException,
    EmptyFileException,
    FileTooLargeException,
    MissingImageException,
    UnsupportedFileTypeException,
    UploadValidator,
)


def make_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    headers = Headers({"content-type": content_type})
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=headers)


def make_valid_image_bytes(fmt: str, size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(120, 20, 40)).save(buffer, format=fmt)
    return buffer.getvalue()


async def run_case(name, coro_factory, expect_exception=None):
    try:
        result = await coro_factory()
        if expect_exception is not None:
            print(f"[FAIL] {name}: expected {expect_exception.__name__}, got result {result}")
            return False
        print(f"[PASS] {name}: {result}")
        return True
    except Exception as exc:  # noqa: BLE001
        if expect_exception is not None and isinstance(exc, expect_exception):
            print(f"[PASS] {name}: raised {type(exc).__name__} -> {exc}")
            return True
        print(f"[FAIL] {name}: raised unexpected {type(exc).__name__} -> {exc}")
        return False


async def main() -> None:
    validator = UploadValidator()
    results = []

    # Missing file
    results.append(await run_case(
        "Missing file",
        lambda: validator.validate(None),
        expect_exception=MissingImageException,
    ))

    # Empty file
    results.append(await run_case(
        "Empty file",
        lambda: validator.validate(make_upload_file("empty.png", b"", "image/png")),
        expect_exception=EmptyFileException,
    ))

    # Unsupported extension
    results.append(await run_case(
        "Unsupported extension",
        lambda: validator.validate(
            make_upload_file("scan.bmp", make_valid_image_bytes("BMP"), "image/bmp")
        ),
        expect_exception=UnsupportedFileTypeException,
    ))

    # Unsupported MIME type (valid extension, mismatched content-type)
    results.append(await run_case(
        "Unsupported MIME type",
        lambda: validator.validate(
            make_upload_file("scan.png", make_valid_image_bytes("PNG"), "application/octet-stream")
        ),
        expect_exception=UnsupportedFileTypeException,
    ))

    # Oversized image
    async def oversized():
        from app.core import upload as upload_module
        original = upload_module.get_settings
        class TinyLimitSettings:
            MAX_UPLOAD_SIZE = 10  # 10 bytes, guaranteed to be exceeded
        upload_module.get_settings = lambda: TinyLimitSettings()
        try:
            return await validator.validate(
                make_upload_file("scan.jpg", make_valid_image_bytes("JPEG"), "image/jpeg")
            )
        finally:
            upload_module.get_settings = original

    results.append(await run_case(
        "Oversized image",
        oversized,
        expect_exception=FileTooLargeException,
    ))

    # Corrupted image (valid extension/mime, garbage bytes)
    results.append(await run_case(
        "Corrupted image",
        lambda: validator.validate(
            make_upload_file("scan.png", b"not-a-real-png-payload", "image/png")
        ),
        expect_exception=CorruptedImageException,
    ))

    # Valid JPEG
    results.append(await run_case(
        "Valid JPEG",
        lambda: validator.validate(
            make_upload_file("slide.jpg", make_valid_image_bytes("JPEG"), "image/jpeg")
        ),
    ))

    # Valid PNG
    results.append(await run_case(
        "Valid PNG",
        lambda: validator.validate(
            make_upload_file("slide.png", make_valid_image_bytes("PNG"), "image/png")
        ),
    ))

    # Valid TIFF
    results.append(await run_case(
        "Valid TIFF",
        lambda: validator.validate(
            make_upload_file("slide.tiff", make_valid_image_bytes("TIFF"), "image/tiff")
        ),
    ))

    print()
    if all(results):
        print(f"ALL {len(results)} CASES PASSED")
    else:
        failed = len(results) - sum(results)
        print(f"{failed} / {len(results)} CASES FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
