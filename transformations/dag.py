"""
DAG Builder - Creates and validates dependency graphs for transformations
"""
from typing import List, Dict, Set
from collections import defaultdict, deque
from .model import TransformationModel

class DAG:
    def __init__(self, models: List[TransformationModel]):
        self.models = {model.name: model for model in models}
        self.graph = self._build_graph()
        self._validate()

    def _build_graph(self) -> Dict[str, List[str]]:
        """Build adjacency list representation of the DAG"""
        graph = defaultdict(list)
        for model in self.models.values():
            for dependency in model.depends_on:
                if dependency not in self.models:
                    raise ValueError(f"Model {model.name} depends on {dependency} which doesn't exist")
                graph[dependency].append(model.name)
        return dict(graph)

    def _validate(self):
        """Check for cycles in the DAG"""
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for model_name in self.models.keys():
            if model_name not in visited:
                if has_cycle(model_name):
                    raise ValueError(f"Cycle detected in DAG involving model: {model_name}")

    def get_execution_order(self) -> List[str]:
        """
        Return topologically sorted list of model names
        (models with no dependencies come first)
        """
        in_degree = defaultdict(int)

        # Calculate in-degrees
        for model in self.models.values():
            if model.name not in in_degree:
                in_degree[model.name] = 0
            for dep in model.depends_on:
                in_degree[model.name] += 1

        # Queue for models with no dependencies
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        execution_order = []

        while queue:
            current = queue.popleft()
            execution_order.append(current)

            # Reduce in-degree for dependent models
            for dependent in self.graph.get(current, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(execution_order) != len(self.models):
            raise ValueError("Could not create valid execution order - possible cycle detected")

        return execution_order

    def visualize(self) -> str:
        """Create a simple text visualization of the DAG"""
        lines = ["DAG Structure:", "=" * 50]

        execution_order = self.get_execution_order()

        for model_name in execution_order:
            model = self.models[model_name]
            deps = ", ".join(model.depends_on) if model.depends_on else "None"
            lines.append(f"{model_name} [{model.model_type.value}]")
            lines.append(f"  └─ Depends on: {deps}")
            lines.append(f"  └─ Status: {model.status}")
            lines.append("")

        return "\n".join(lines)
