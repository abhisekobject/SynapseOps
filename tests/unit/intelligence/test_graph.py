from backend.intelligence.graph import DependencyGraph


class TestDependencyGraph:
    def test_graph_initialization(self):
        graph = DependencyGraph()
        nodes = graph.get_all_nodes()
        assert "sim-gateway" in nodes
        assert "sim-api" in nodes
        assert "sim-worker" in nodes
        assert "database" in nodes
        assert "redis" in nodes

    def test_direct_dependencies(self):
        graph = DependencyGraph()
        deps = graph.get_direct_dependencies("sim-api")
        assert "sim-worker" in deps
        assert "sim-gateway" not in deps

        deps = graph.get_direct_dependencies("sim-worker")
        assert "database" in deps
        assert "redis" in deps

    def test_transitive_dependencies(self):
        graph = DependencyGraph()
        deps = graph.get_transitive_dependencies("sim-gateway")
        assert "sim-api" in deps
        assert "sim-worker" in deps
        assert "database" in deps
        assert "redis" in deps

    def test_direct_dependents(self):
        graph = DependencyGraph()
        deps = graph.get_direct_dependents("sim-worker")
        assert "sim-api" in deps

    def test_transitive_dependents(self):
        graph = DependencyGraph()
        deps = graph.get_transitive_dependents("database")
        assert "sim-worker" in deps
        assert "sim-api" in deps
        assert "sim-gateway" in deps

    def test_unknown_node_safety(self):
        graph = DependencyGraph()
        assert graph.get_direct_dependencies("unknown") == []
        assert graph.get_transitive_dependents("unknown") == []
