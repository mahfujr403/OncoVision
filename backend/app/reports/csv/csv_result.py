"""CSV Export Result domain model (Phase 6.3, ADR-039).

`CSVExportResult` is the immutable artifact produced by
`CSVExportBuilder`: a single generation's fully-serialized CSV document
(`content`) plus the metadata a future export endpoint (Phase 6.5) needs
to return it as a downloadable file, bundled together for
`CSVExportService` to return.

Per ADR-039, CSV Export is read-only and dynamically generated --
`CSVExportResult` has no corresponding database table or ORM model, and
no field on it is ever written back to Prediction History or Prediction
Analytics. `content` is produced exactly once and never mutated.
"""

from pydantic import BaseModel, ConfigDict, Field

#: Content-Type header value a future export endpoint should use when
#: returning `CSVExportResult.content` as a downloadable file.
CSV_CONTENT_TYPE: str = "text/csv; charset=utf-8"


class CSVExportResult(BaseModel):
    """Immutable, fully-serialized CSV document produced by one export run.

    Constructed exactly once per export by `CSVExportBuilder`. Never
    constructed, mutated, or re-serialized by any other component.
    """

    model_config = ConfigDict(frozen=True)

    export_id: str = Field(description="Unique identifier for this CSV export generation run.")
    user_id: str = Field(description="Unique identifier of the user this export was generated for.")
    generated_at: str = Field(description="ISO 8601 timestamp of when this export was generated.")
    filename: str = Field(description="Suggested filename for this CSV document, including extension.")
    content_type: str = Field(
        default=CSV_CONTENT_TYPE,
        description="MIME content type a future export endpoint should serve this document as.",
    )
    content: str = Field(
        description=(
            "The complete, UTF-8 encoded CSV document -- a Prediction "
            "History section followed by an Analytics Summary section, "
            "each with its own header row."
        )
    )
    history_row_count: int = Field(
        default=0,
        description="Number of Prediction History data rows included in `content` (excludes the header row).",
    )

    @classmethod
    def empty(cls, export_id: str, user_id: str, generated_at: str, filename: str, content: str) -> "CSVExportResult":
        """Return a `CSVExportResult` for a user with no matching prediction history records.

        `content` still carries valid, header-only CSV sections (and a
        zero-data Analytics Summary section) -- an empty history
        collection is not an error condition (ADR-039).
        """
        return cls(
            export_id=export_id,
            user_id=user_id,
            generated_at=generated_at,
            filename=filename,
            content=content,
            history_row_count=0,
        )
