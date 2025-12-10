"""Tests for rustworkx-backed DependencyGraph."""

import pytest
from jnkn.core.graph import DependencyGraph, TokenIndex
from jnkn.core.types import Edge, Node, NodeType, RelationshipType


@pytest.fixture
def graph():
    return DependencyGraph()


@pytest.fixture
def sample_nodes():
    return [
        Node(id="a", name="Service A", type=NodeType.CODE_FILE, tokens=["service", "a"]),
        Node(id="b", name="Database B", type=NodeType.INFRA_RESOURCE, tokens=["database", "b"]),
        Node(id="c", name="Config C", type=NodeType.ENV_VAR, tokens=["config", "c"]),
    ]


def test_add_get_node(graph, sample_nodes):
    node_a = sample_nodes[0]
    graph.add_node(node_a)
    
    assert graph.has_node("a")
    assert graph.get_node("a") == node_a
    assert graph.node_count == 1
    
    # Test update
    updated_node = node_a.model_copy(update={"name": "Updated A"})
    graph.add_node(updated_node)
    assert graph.get_node("a").name == "Updated A"
    assert graph.node_count == 1  # Should not duplicate


def test_add_edge(graph, sample_nodes):
    a, b, c = sample_nodes
    graph.add_node(a)
    graph.add_node(b)
    
    edge = Edge(
        source_id=a.id,
        target_id=b.id,
        type=RelationshipType.READS
    )
    graph.add_edge(edge)
    
    assert graph.has_edge(a.id, b.id)
    assert not graph.has_edge(b.id, a.id)  # Directed
    assert graph.edge_count == 1


def test_traversal(graph, sample_nodes):
    a, b, c = sample_nodes
    # A -> B -> C
    graph.add_node(a)
    graph.add_node(b)
    graph.add_node(c)
    
    graph.add_edge(Edge(source_id=a.id, target_id=b.id, type=RelationshipType.READS))
    graph.add_edge(Edge(source_id=b.id, target_id=c.id, type=RelationshipType.READS))
    
    # Descendants
    desc_a = graph.get_descendants(a.id)
    assert b.id in desc_a
    assert c.id in desc_a
    assert len(desc_a) == 2
    
    # Ancestors
    anc_c = graph.get_ancestors(c.id)
    assert b.id in anc_c
    assert a.id in anc_c
    assert len(anc_c) == 2


def test_token_indexing(graph, sample_nodes):
    a, b, c = sample_nodes
    graph.add_node(a) # tokens: service, a
    graph.add_node(b) # tokens: database, b
    
    # Exact match
    res = graph.find_nodes_by_tokens(["service"])
    assert len(res) == 1
    assert res[0].id == a.id
    
    # No match
    assert len(graph.find_nodes_by_tokens(["missing"])) == 0
    
    # Multiple nodes via same token (simulated)
    d = Node(id="d", name="Service D", type=NodeType.CODE_FILE, tokens=["service", "d"])
    graph.add_node(d)
    
    res_multi = graph.find_nodes_by_tokens(["service"])
    assert len(res_multi) == 2
    assert {n.id for n in res_multi} == {"a", "d"}


def test_remove_node(graph, sample_nodes):
    a, b, c = sample_nodes
    graph.add_node(a)
    graph.add_node(b)
    graph.add_edge(Edge(source_id=a.id, target_id=b.id, type=RelationshipType.READS))
    
    assert graph.node_count == 2
    assert graph.edge_count == 1
    
    graph.remove_node(a.id)
    
    assert graph.node_count == 1
    assert not graph.has_node(a.id)
    assert graph.has_node(b.id)
    # Edge should be gone (implicitly in rustworkx, explicitly tracked in counts usually)
    assert graph.edge_count == 0