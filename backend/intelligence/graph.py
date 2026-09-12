import networkx as nx


class DependencyGraph:
    """Represents the static dependency topology of the simulated infrastructure.

    Nodes: service identifiers (e.g., 'sim-gateway', 'database')
    Edges: A -> B strictly denotes 'A depends on B'
    """

    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._build_topology()

    def _build_topology(self) -> None:
        """Construct the static dependency graph."""
        nodes = ["sim-gateway", "sim-api", "sim-worker", "database", "redis"]
        self._graph.add_nodes_from(nodes)

        # Edges represent "depends on"
        self._graph.add_edge("sim-gateway", "sim-api")
        self._graph.add_edge("sim-api", "sim-worker")
        self._graph.add_edge("sim-worker", "database")
        self._graph.add_edge("sim-worker", "redis")

    def get_direct_dependencies(self, node: str) -> list[str]:
        """Return the list of components that 'node' depends on directly."""
        if node not in self._graph:
            return []
        return list(self._graph.successors(node))

    def get_transitive_dependencies(self, node: str) -> list[str]:
        """Return the list of components that 'node' depends on (direct + indirect)."""
        if node not in self._graph:
            return []
        return list(nx.descendants(self._graph, node))

    def get_direct_dependents(self, node: str) -> list[str]:
        """Return the list of components that depend directly on 'node'."""
        if node not in self._graph:
            return []
        return list(self._graph.predecessors(node))

    def get_transitive_dependents(self, node: str) -> list[str]:
        """Return the list of components that depend on 'node' (direct + indirect)."""
        if node not in self._graph:
            return []
        return list(nx.ancestors(self._graph, node))

    def get_all_nodes(self) -> list[str]:
        """Return all node names."""
        return list(self._graph.nodes)

    def to_dict(self) -> dict:
        """Return a dictionary representation of the graph."""
        return {
            "nodes": list(self._graph.nodes),
            "edges": [
                {"source": u, "target": v, "relationship": "depends_on"}
                for u, v in self._graph.edges
            ],
        }
