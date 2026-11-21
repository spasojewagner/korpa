from collections.abc import Callable, Iterator, Mapping

from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLError,
    InlineFragmentNode,
    OperationDefinitionNode,
    SelectionSetNode,
    ValidationContext,
    ValidationRule,
    value_from_ast_untyped,
)
from strawberry.extensions import (
    AddValidationRules,
    MaxAliasesLimiter,
    MaxTokensLimiter,
    QueryDepthLimiter,
    SchemaExtension,
)

from korpa_api.gql.context import FORMAT_CAP, NAME_CAP, OBSERVATION_CAP, Context

COST_LIMIT = 5000


class CostRule(ValidationRule):
    def __init__(self, context: ValidationContext, variables: Mapping[str, object]) -> None:
        super().__init__(context)
        self.variables = dict(variables)

    def enter_operation_definition(self, node: OperationDefinitionNode, *_: object) -> None:
        variables = dict(self.variables)
        for definition in node.variable_definitions or ():
            if definition.default_value is not None:
                variables.setdefault(
                    definition.variable.name.value, value_from_ast_untyped(definition.default_value)
                )
        cost = self.cost(node.selection_set, variables, frozenset())
        if cost > COST_LIMIT:
            self.report_error(
                GraphQLError(
                    f"Query cost {cost} exceeds maximum {COST_LIMIT}",
                    nodes=[node],
                )
            )

    def cost(
        self,
        selection: SelectionSetNode,
        variables: dict[str, object],
        fragments: frozenset[str],
    ) -> int:
        total = 0
        for node in selection.selections:
            if isinstance(node, FieldNode):
                arguments = {
                    arg.name.value: value_from_ast_untyped(arg.value, variables)
                    for arg in node.arguments or ()
                }
                name = node.name.value
                multiplier = 1
                if name == "products":
                    codes = arguments.get("barcodes")
                    multiplier = min(50, len(codes)) if isinstance(codes, list) else 50
                elif name == "categories":
                    multiplier = 25
                elif name == "prices":
                    multiplier = FORMAT_CAP
                elif name == "names":
                    multiplier = NAME_CAP
                elif name in {"history", "changes"}:
                    key, default, maximum = (
                        ("months", 12, 24) if name == "history" else ("days", 30, 120)
                    )
                    value = arguments.get(key, default)
                    multiplier = min(
                        OBSERVATION_CAP,
                        FORMAT_CAP
                        * (max(1, min(maximum, value)) if type(value) is int else maximum),
                    )
                total += 1 + multiplier * (
                    self.cost(node.selection_set, variables, fragments) if node.selection_set else 0
                )
            elif isinstance(node, InlineFragmentNode):
                total += self.cost(node.selection_set, variables, fragments)
            elif isinstance(node, FragmentSpreadNode) and node.name.value not in fragments:
                fragment = self.context.get_fragment(node.name.value)
                if fragment is not None:
                    total += self.cost(
                        fragment.selection_set, variables, fragments | {node.name.value}
                    )
            if total > COST_LIMIT:
                return COST_LIMIT + 1
        return total


class CostExtension(AddValidationRules):
    def __init__(self) -> None:
        super().__init__([])

    def on_operation(self) -> Iterator[None]:
        values: Mapping[str, object] = self.execution_context.variables or {}

        class RequestCostRule(CostRule):
            def __init__(self, context: ValidationContext) -> None:
                super().__init__(context, values)

        self.validation_rules = [RequestCostRule]
        yield from super().on_operation()


class SourceDateExtension(SchemaExtension):
    def get_results(self) -> dict[str, object]:
        context = self.execution_context.context
        return {"as_of": context.as_of.isoformat()} if isinstance(context, Context) else {}


def extensions() -> list[Callable[[], SchemaExtension]]:
    return [
        lambda: QueryDepthLimiter(max_depth=6),
        lambda: MaxAliasesLimiter(max_alias_count=15),
        lambda: MaxTokensLimiter(max_token_count=1000),
        CostExtension,
        SourceDateExtension,
    ]
