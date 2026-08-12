"""PDF Report Builder (Phase 6.4, ADR-040).

`PDFBuilder` is the pure rendering layer that assembles an immutable
`PDFExportResult` from an already-retrieved `PredictionHistory`
collection and an already-computed `PredictionAnalyticsResult`. It never
accesses the database, never verifies ownership, never performs
inference, and never recalculates any statistic -- it only formats
values already present on the supplied domain objects into a PDF
document, mirroring the read-only, copy-only convention already
established by `CSVExportBuilder`.

Rendering is implemented with ReportLab's Platypus layer
(`SimpleDocTemplate` + flowables), the same PDF library already declared
for this project (`Project Context` -> Technology Stack -> Backend ->
ReportLab). The generated document is A4 portrait and contains, in
order:

    1. Report title
    2. Generation metadata (generated-at timestamp, user id)
    3. Analytics Summary section (a metric/value table)
    4. Prediction History section (a per-record table)

Every numeric value is formatted through a single pair of helpers
(`_format_percentage` / `_format_ratio`) so formatting stays
deterministic across every field and both the summary and history
sections. `Table` cells hold plain Python strings only (never
ReportLab's mini-XML `Paragraph` markup), so dynamic values -- request
IDs, predicted class labels, user IDs -- can never be misinterpreted as
markup; ReportLab draws plain table-cell strings directly, unescaped and
unparsed.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.reports.pdf.enums import PDFPageSize
from app.reports.pdf.pdf_result import PDFExportResult
from app.utils.environment import generate_request_id, get_current_timestamp

logger = get_logger(__name__)

#: Deterministic column order for the Prediction History table.
#: `PDFBuilder` never reorders, renames, or omits these columns.
HISTORY_COLUMNS: tuple[str, ...] = (
    "Request ID",
    "Date",
    "Predicted Class",
    "Confidence",
    "Agreement Ratio",
    "Status",
)

#: Column widths (cm) for the Prediction History table, matching
#: `HISTORY_COLUMNS` position for position.
_HISTORY_COLUMN_WIDTHS: tuple[float, ...] = (3.4, 3.6, 3.2, 2.6, 2.8, 2.0)

#: Physical page size each supported `PDFPageSize` renders as.
_PAGE_SIZES: dict[PDFPageSize, tuple[float, float]] = {
    PDFPageSize.A4: A4,
}

_BRAND_COLOR = colors.HexColor("#1F3B57")
_ALT_ROW_COLOR = colors.whitesmoke


class PDFBuilder:
    """Builds immutable `PDFExportResult` objects from prediction history and analytics.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `CSVExportBuilder`.
    """

    def build(
        self,
        user_id: str,
        history: list[PredictionHistory],
        analytics: PredictionAnalyticsResult,
        page_size: PDFPageSize = PDFPageSize.A4,
    ) -> PDFExportResult:
        """Build a `PDFExportResult` from already-retrieved data.

        Args:
            user_id: Identifier of the user this export is generated
                for. Copied directly onto the resulting
                `PDFExportResult` -- this method performs no ownership
                verification of its own; `history` and `analytics` are
                trusted to already be scoped to `user_id` by the
                repository/service calls that produced them.
            history: The user's `PredictionHistory` records to render
                into the Prediction History table. May be supplied in
                any order. May be empty.
            analytics: The user's already-computed
                `PredictionAnalyticsResult`, rendered into the Analytics
                Summary section verbatim -- no recalculation occurs
                here.
            page_size: The `PDFPageSize` to render with. Defaults to,
                and in this phase can only be, `PDFPageSize.A4` portrait.

        Returns:
            An immutable `PDFExportResult` carrying the complete,
            rendered PDF document as raw bytes.
        """
        export_id = generate_request_id()
        generated_at = get_current_timestamp()
        filename = self._build_filename(export_id)

        content = self._render(
            user_id=user_id,
            history=history,
            analytics=analytics,
            generated_at=generated_at,
            page_size=page_size,
        )

        if not history:
            logger.info(
                "PDF export built with empty history collection: user_id=%s export_id=%s",
                user_id,
                export_id,
            )
            return PDFExportResult.empty(
                export_id=export_id,
                user_id=user_id,
                generated_at=generated_at,
                filename=filename,
                content=content,
            )

        result = PDFExportResult(
            export_id=export_id,
            user_id=user_id,
            generated_at=generated_at,
            filename=filename,
            content=content,
            history_row_count=len(history),
        )

        logger.info(
            "PDF export built: user_id=%s export_id=%s record_count=%d",
            user_id,
            export_id,
            len(history),
        )

        return result

    @classmethod
    def _render(
        cls,
        user_id: str,
        history: list[PredictionHistory],
        analytics: PredictionAnalyticsResult,
        generated_at: str,
        page_size: PDFPageSize,
    ) -> bytes:
        """Render the complete PDF document and return it as raw bytes."""
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=_PAGE_SIZES[page_size],
            topMargin=2.2 * cm,
            bottomMargin=2.0 * cm,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            title="OncoVision AI Prediction Report",
        )

        styles = getSampleStyleSheet()
        story = [
            Paragraph("OncoVision AI \u2014 Prediction Report", styles["Title"]),
            Spacer(1, 0.4 * cm),
            cls._build_metadata_table(user_id=user_id, generated_at=generated_at),
            Spacer(1, 0.6 * cm),
            Paragraph("Analytics Summary", styles["Heading2"]),
            Spacer(1, 0.2 * cm),
            cls._build_analytics_table(analytics),
            Spacer(1, 0.6 * cm),
            Paragraph("Prediction History", styles["Heading2"]),
            Spacer(1, 0.2 * cm),
            cls._build_history_table(history),
        ]

        document.build(story, onFirstPage=cls._draw_footer, onLaterPages=cls._draw_footer)
        return buffer.getvalue()

    @staticmethod
    def _build_metadata_table(user_id: str, generated_at: str) -> Table:
        """Build the report's generation metadata table (generated-at, user id)."""
        data = [
            ["Generated At", generated_at],
            ["User ID", user_id],
        ]
        table = Table(data, colWidths=[4.0 * cm, 12.6 * cm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    @staticmethod
    def _build_analytics_table(analytics: PredictionAnalyticsResult) -> Table:
        """Build the Analytics Summary metric/value table from `analytics` verbatim."""
        rows: list[list[str]] = [
            ["Metric", "Value"],
            ["Total Predictions", str(analytics.total_predictions)],
            ["Successful Predictions", str(analytics.successful_predictions)],
            ["Failed Predictions", str(analytics.failed_predictions)],
            ["Average Confidence", _format_percentage(analytics.average_confidence)],
            ["Average Agreement Ratio", _format_ratio(analytics.average_agreement_ratio)],
            ["Most Predicted Class", analytics.most_predicted_class or "N/A"],
        ]

        table = Table(rows, colWidths=[7.0 * cm, 9.6 * cm], hAlign="LEFT")
        table.setStyle(_header_row_style(header_row=0, data_rows=len(rows) - 1))
        return table

    @staticmethod
    def _build_history_table(history: list[PredictionHistory]) -> Table:
        """Build the Prediction History table, one row per `PredictionHistory` record."""
        rows: list[list[str]] = [list(HISTORY_COLUMNS)]

        if not history:
            rows.append(["No prediction history available.", "", "", "", "", ""])
        else:
            for record in history:
                rows.append(
                    [
                        record.request_id,
                        record.created_at,
                        record.summary.predicted_class or "N/A",
                        _format_percentage(record.summary.confidence),
                        _format_ratio(record.summary.agreement_ratio),
                        record.status.value,
                    ]
                )

        column_widths = [width * cm for width in _HISTORY_COLUMN_WIDTHS]
        table = Table(rows, colWidths=column_widths, hAlign="LEFT", repeatRows=1)

        style_commands = _header_row_style(header_row=0, data_rows=len(rows) - 1, font_size=8)
        if not history:
            style_commands.add("SPAN", (0, 1), (-1, 1))
        table.setStyle(style_commands)
        return table

    @staticmethod
    def _draw_footer(canvas, document) -> None:
        """Draw the page footer (report label + page number) on every page."""
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.8 * cm, 1.2 * cm, "OncoVision AI \u2014 Prediction Report")
        canvas.drawRightString(
            document.pagesize[0] - 1.8 * cm, 1.2 * cm, f"Page {canvas.getPageNumber()}"
        )
        canvas.restoreState()

    @staticmethod
    def _build_filename(export_id: str) -> str:
        """Return the suggested filename for one export run, unique per `export_id`."""
        return f"oncovision_prediction_report_{export_id}.pdf"


def _header_row_style(header_row: int, data_rows: int, font_size: int = 9) -> TableStyle:
    """Return the shared header/zebra-striped `TableStyle` used by both report tables."""
    return TableStyle(
        [
            ("BACKGROUND", (0, header_row), (-1, header_row), _BRAND_COLOR),
            ("TEXTCOLOR", (0, header_row), (-1, header_row), colors.white),
            ("FONTNAME", (0, header_row), (-1, header_row), "Helvetica-Bold"),
            ("FONTNAME", (0, header_row + 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, header_row + 1), (-1, -1), [_ALT_ROW_COLOR, colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def _format_percentage(value: float) -> str:
    """Format `value` (already a 0-100 percentage) with two fixed decimal places."""
    return f"{value:.2f}%"


def _format_ratio(value: float) -> str:
    """Format `value` (a 0-1 ratio) with four fixed decimal places."""
    return f"{value:.4f}"
