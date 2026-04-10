from __future__ import annotations

from typing import Any, cast

from src.application.batch_generate import BatchGenerateUseCase


class StubGenerateUseCase:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def execute(self, req: Any) -> dict[str, str]:
        self.requests.append(req)
        return {"status": "ok", "pmid": req.pmid, "output_path": req.output_dir}


def test_batch_generate_propagates_all_request_fields() -> None:
    stub = StubGenerateUseCase()
    use_case = BatchGenerateUseCase(generate_uc=cast("Any", stub))

    result = use_case.execute(
        pmids=["123", "456"],
        figure_type="flowchart",
        language="en",
        output_size="1024x1024",
        output_dir="custom-output",
    )

    assert result["success"] == 2
    assert len(stub.requests) == 2
    assert stub.requests[0].figure_type == "flowchart"
    assert stub.requests[0].language == "en"
    assert stub.requests[0].output_size == "1024x1024"
    assert stub.requests[0].output_dir == "custom-output"
