from typing import Any, Dict

from ..exceptions import UnhandledBranchError
from ..model import AggregatedIntrospectionMixin, InterpreterContext
from ..value_providers import StaticValueOrValueProvider, ValueProvider
from .interpretation import Interpretation


class SwitchInterpretation(AggregatedIntrospectionMixin, Interpretation, name="switch"):
    __slots__ = (
        "switch_on",
        "interpretations",
        "default",
        "normalization",
    )

    def __init__(
        self,
        switch_on: StaticValueOrValueProvider,
        cases: Dict[str, dict],
        default: Dict[str, Any] = None,
        normalization: Dict[str, Any] = None,
    ):
        self.switch_on = ValueProvider.garuntee_value_provider(switch_on)
        self.interpretations = {
            field_value: Interpretation.from_file_arguments(**interpretation)
            for field_value, interpretation in cases.items()
        }
        self.default = (
            Interpretation.from_file_arguments(**default) if default else None
        )
        self.normalization = normalization or {}

    def all_subordinate_components(self):
        yield from self.interpretations.values()
        if self.default:
            yield self.default

    def interpret(self, context: InterpreterContext):
        value_to_look_for = self.switch_on.normalize_single_value(
            context, **self.normalization
        )
        if value_to_look_for not in self.interpretations:
            if self.default:
                return self.default.interpret(context)
            raise UnhandledBranchError(value_to_look_for)
        return self.interpretations[value_to_look_for].interpret(context)