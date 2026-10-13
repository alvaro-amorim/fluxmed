from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from fluxmed.application.optimization.results import (
    OptimizationResultNotFoundError,
    OptimizationResultService,
)
from fluxmed.application.optimization.routing_matrix import OptimizationRoutingError
from fluxmed.application.optimization.runtime import OptimizationRunCoordinator
from fluxmed.application.optimization.service import (
    OptimizationInputError,
    OptimizationValidationMismatchError,
)


@pytest.mark.parametrize(
    ("error", "expected_code", "expected_message"),
    [
        (
            OptimizationValidationMismatchError("secret mismatch details"),
            "OPTIMIZER_VALIDATION_MISMATCH",
            "A validação independente divergiu do resultado do otimizador.",
        ),
        (
            OptimizationRoutingError("secret routing details"),
            "ROUTING_UNAVAILABLE",
            "Não foi possível calcular as rotas para esta otimização.",
        ),
        (
            OptimizationInputError("secret input details"),
            "OPTIMIZATION_INVALID",
            "A otimização não pôde ser concluída com os dados atuais.",
        ),
        (
            RuntimeError("password=super-secret"),
            "OPTIMIZATION_FAILED",
            "A otimização falhou inesperadamente.",
        ),
    ],
)
def test_optimizer_failures_are_mapped_to_sanitized_public_errors(
    error: Exception,
    expected_code: str,
    expected_message: str,
) -> None:
    code, message = OptimizationRunCoordinator._public_failure(error)

    assert code == expected_code
    assert message == expected_message
    assert "secret" not in message.lower()
    assert "password" not in message.lower()


def test_unvalidated_completed_run_is_not_exposed_as_a_result() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = SimpleNamespace(
        status="COMPLETED",
        validated=False,
        operation_revision_id=object(),
    )

    with pytest.raises(OptimizationResultNotFoundError):
        OptimizationResultService(session).get_result(object())  # type: ignore[arg-type]

    session.get.assert_called_once()
