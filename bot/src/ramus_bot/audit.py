from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import Claim, Decision


@dataclass(frozen=True)
class AuditReport:
    path: Path


def write_decision_report(
    decision: Decision, claims: list[Claim], output_dir: str
) -> AuditReport:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"bounty_{decision.bounty_id}_{timestamp}.md"

    claim_map = {claim.claim_id: claim for claim in claims}
    lines = [
        f"# Bounty {decision.bounty_id} Decision",
        "",
        f"Timestamp (UTC): {timestamp}",
        f"Winner claim ID: {decision.winner_claim_id}",
        "",
        "## Reasoning",
        decision.reasoning,
        "",
        "## Claims",
    ]

    for claim_id, score in decision.scores.items():
        claim = claim_map.get(claim_id)
        if not claim:
            continue
        lines.extend(
            [
                f"### Claim {claim_id}",
                f"Issuer: {claim.issuer}",
                f"Created at: {claim.created_at.isoformat()}",
                f"Score: {score:.2f}",
                "",
                f"Title: {claim.title}",
                "",
                "Description:",
                claim.description,
                "",
            ]
        )

    path.write_text("\n".join(lines))
    return AuditReport(path=path)
