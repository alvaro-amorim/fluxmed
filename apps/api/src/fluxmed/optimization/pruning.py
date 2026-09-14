from collections import Counter
from dataclasses import dataclass, field

from fluxmed.optimization.models import PruningReason, PruningSummary


@dataclass(slots=True)
class PruningTracker:
    _counts: Counter[PruningReason] = field(default_factory=Counter)
    avoided_full_evaluations: int = 0

    def record(self, reason: PruningReason, *, avoided_full_evaluation: bool = False) -> None:
        self._counts[reason] += 1
        if avoided_full_evaluation:
            self.avoided_full_evaluations += 1

    def merge(self, summary: PruningSummary) -> None:
        for raw_reason, count in summary.pruned_by_reason.items():
            self._counts[PruningReason(raw_reason)] += count
        self.avoided_full_evaluations += summary.avoided_full_evaluations

    def summary(self) -> PruningSummary:
        counts = {reason.value: count for reason, count in sorted(self._counts.items())}
        return PruningSummary(
            total_pruned=sum(self._counts.values()),
            pruned_by_reason=counts,
            avoided_full_evaluations=self.avoided_full_evaluations,
        )
