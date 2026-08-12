"""PDF Export Result domain model (Phase 6.4, ADR-040).

`PDFExportResult` is the immutable artifact produced by `PDFBuilder`: a
single generation's fully-rendered PDF document (`content`, raw PDF
bytes) plus the metadata a future export endpoint (Phase 6.5) needs to
return it as a downloadable file, bundled together for
`PDFExportService` to return. Mirrors `app.reports.csv.csv_result.CSVExportResult`
exactly, differing only in `content` being binary rather than text.

Per ADR-040, PDF Export is read-only and dynamically generated --
`PDFExportResult` has no corresponding database table or ORM model, and
no field on it is ever written back to Prediction History or Prediction
Analytics. `content` is produced exactly once and never mutated.
"""

from pydantic import BaseModel, ConfigDict, Field

#: Content-Type header value a future export endpoint should use when
#: returning `PDFExportResult.content` as a downloadable file.
PDF_CONTENT_TYPE: str = "application/pdf"


class PDFExportResult(BaseModel):
    """Immutable, fully-rendered PDF document produced by one export run.

    Constructed exactly once per export by `PDFBuilder`. Never
    constructed, mutated, or re-rendered by any other component.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    export_id: str = Field(description="Unique identifier for this PDF export generation run.")
    user_id: str = Field(description="Unique identifier of the user this export was generated for.")
    generated_at: str = Field(description="ISO 8601 timestamp of when this export was generated.")
    filename: str = Field(description="Suggested filename for this PDF document, including extension.")
    content_type: str = Field(
        default=PDF_CONTENT_TYPE,
        description="MIME content type a future export endpoint should serve this document as.",
    )
    content: bytes = Field(description="The complete, rendered PDF document as raw bytes.")
    history_row_count: int = Field(
        default=0,
        description="Number of Prediction History rows included in the report's history table.",
    )

    @classmethod
    def empty(
        cls, export_id: str, user_id: str, generated_at: str, filename: str, content: bytes
    ) -> "PDFExportResult":
        """Return a `PDFExportResult` for a user with no matching prediction history records.

        `content` still carries a valid, fully-rendered PDF document
        (with a zero-data Analytics Summary section and an empty
        Prediction History table) -- an empty history collection is not
        an error condition (ADR-040), mirroring
        `CSVExportResult.empty()`.
        """
        return cls(
            export_id=export_id,
            user_id=user_id,
            generated_at=generated_at,
            filename=filename,
            content=content,
            history_row_count=0,
        )
