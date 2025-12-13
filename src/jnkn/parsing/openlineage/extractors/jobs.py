# FILE: src/jnkn/parsing/openlineage/extractors/jobs.py
"""
Job Extractor for OpenLineage.

This module handles the extraction of 'Job' entities from OpenLineage events.
"""

import json
import re
from typing import Generator, List, Union

from ....core.types import Edge, Node, NodeType
from ...base import ExtractionContext


class JobExtractor:
    """
    Extract Job definitions from OpenLineage events.
    """

    name = "openlineage_jobs"
    priority = 100

    def can_extract(self, ctx: ExtractionContext) -> bool:
        return '"job"' in ctx.text and '"namespace"' in ctx.text

    def extract(self, ctx: ExtractionContext) -> Generator[Union[Node, Edge], None, None]:
        try:
            data = json.loads(ctx.text)
        except json.JSONDecodeError:
            return

        events = data if isinstance(data, list) else [data] if isinstance(data, dict) else []

        for event in events:
            if event.get("eventType") not in ("COMPLETE", "RUNNING"):
                continue

            job = event.get("job", {})
            namespace = job.get("namespace", "default")
            name = job.get("name")

            if not name:
                continue

            job_id = f"job:{namespace}/{name}"

            if job_id in ctx.seen_ids:
                continue
            ctx.seen_ids.add(job_id)

            # Use generic create_node to ensure path is set to the .json file
            yield ctx.create_node(
                id=job_id,
                name=name,
                type=NodeType.JOB,
                tokens=self._tokenize(name),
                metadata={
                    "namespace": namespace,
                    "source": "openlineage",
                    "facets": job.get("facets", {}),
                    "run_id": event.get("run", {}).get("runId"),
                    "event_time": event.get("eventTime"),
                },
            )

            # Link file to job (File CONTAINS Job)
            yield ctx.create_contains_edge(target_id=job_id)

    def _tokenize(self, name: str) -> List[str]:
        return [t for t in re.split(r"[_\-./]", name.lower()) if len(t) >= 2]