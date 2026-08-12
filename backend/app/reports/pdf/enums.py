"""PDF Export enumerations (Phase 6.4, ADR-040).

Mirrors the convention already established by `app.reports.enums` and
`app.history.enums`: each enum here is owned independently by the
`app.reports.pdf` package and never imports from the API layer.
"""

from enum import Enum


class PDFPageSize(str, Enum):
    """Page size a PDF report may be rendered with.

    Only `A4` (portrait) is supported in this phase, matching the
    explicit Phase 6.4 requirement. The enum exists so `PDFBuilder` /
    `PDFValidator` already carry a stable, typed contract for page-size
    selection, ready for future page sizes (e.g. `LETTER`) to extend
    without changing the shape of the existing request surface.
    `PDFValidator` rejects any value other than `A4` as an unsupported
    option until a future phase adds real support for it.
    """

    A4 = "a4"
