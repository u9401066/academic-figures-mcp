"""Use case: generate figures for multiple PMIDs in sequence."""

from __future__ import annotations

from src.application.contracts import (
    AggregateKind,
    ApplicationStatus,
    serialize_aggregate_contract,
)
from src.application.generate_figure import GenerateFigureRequest, GenerateFigureUseCase


class BatchGenerateUseCase:
    def __init__(self, generate_uc: GenerateFigureUseCase) -> None:
        self._generate_uc = generate_uc

    def execute(
        self,
        pmids: list[str],
        figure_type: str = "auto",
        language: str = "zh-TW",
        output_size: str = "1024x1536",
        output_dir: str | None = None,
    ) -> dict[str, object]:
        results = []
        for pmid in pmids:
            req = GenerateFigureRequest(
                pmid=pmid,
                figure_type=figure_type,
                language=language,
                output_size=output_size,
                output_dir=output_dir,
            )
            results.append(self._generate_uc.execute(req))

        success = sum(1 for r in results if r.get("status") == "ok")
        payload = {
            "status": ApplicationStatus.OK.value,
            "total": len(pmids),
            "success": success,
            "failed": len(pmids) - success,
            "output_dir": output_dir,
            "language": language,
            "output_size": output_size,
            "results": results,
        }
        payload.update(
            serialize_aggregate_contract(
                kind=AggregateKind.BATCH_GENERATE,
                item_count=len(pmids),
                total_count=len(pmids),
                success_count=success,
                failed_count=len(pmids) - success,
            )
        )
        return payload
