"""Create DOT code with method-calls."""

import typing

from . import base
from . import quoting

__all__ = ['Dot']


class Dot(quoting.Quote, base.Base):
    """Assemble, save, and render DOT source code, open result in viewer."""

    directed: bool

    _comment = '// %s\n'
    _head: str
    _head_strict: str
    _subgraph = 'subgraph %s{\n'
    _subgraph_plain = '%s{\n'
    _node = _attr = '\t%s%s\n'
    _edge: str
    _edge_plain: str
    _attr_plain = _attr % ('%s', '')
    _tail = '}\n'

    def __init__(self, name=None, comment=None,
                 graph_attr=None, node_attr=None, edge_attr=None, body=None,
                 strict=False, **kwargs):
        super().__init__(**kwargs)

        self.name = name
        self.comment = comment

        self.graph_attr = dict(graph_attr) if graph_attr is not None else {}
        self.node_attr = dict(node_attr) if node_attr is not None else {}
        self.edge_attr = dict(edge_attr) if edge_attr is not None else {}

        self.body = list(body) if body is not None else []

        self.strict = strict

    def _copy_kwargs(self, **kwargs):
        """Return the kwargs to create a copy of the instance."""
        return super()._copy_kwargs(name=self.name,
                                    comment=self.comment,
                                    graph_attr=dict(self.graph_attr),
                                    node_attr=dict(self.node_attr),
                                    edge_attr=dict(self.edge_attr),
                                    body=list(self.body),
                                    strict=self.strict)

    def clear(self, keep_attrs=False):
        """Reset content to an empty body, clear graph/node/egde_attr mappings.

        Args:
            keep_attrs (bool): preserve graph/node/egde_attr mappings
        """
        if not keep_attrs:
            for a in (self.graph_attr, self.node_attr, self.edge_attr):
                a.clear()
        del self.body[:]

    def __iter__(self, subgraph=False) -> typing.Iterator[str]:
        r"""Yield the DOT source code line by line (as graph or subgraph).

        Yields: Line ending with a newline (``'\n'``).
        """
        if self.comment:
            yield self._comment % self.comment

        if subgraph:
            if self.strict:
                raise ValueError('subgraphs cannot be strict')
            head = self._subgraph if self.name else self._subgraph_plain
        else:
            head = self._head_strict if self.strict else self._head
        yield head % (self._quote(self.name) + ' ' if self.name else '')

        for kw in ('graph', 'node', 'edge'):
            attrs = getattr(self, f'{kw}_attr')
            if attrs:
                yield self._attr % (kw, self._attr_list(None, attrs))

        for line in self.body:
            yield line

        yield self._tail

    def node(self, name, label=None, _attributes=None, **attrs):
        """Create a node.

        Args:
            name: Unique identifier for the node inside the source.
            label: Caption to be displayed (defaults to the node ``name``).
            attrs: Any additional node attributes (must be strings).
        """
        name = self._quote(name)
        attr_list = self._attr_list(label, attrs, _attributes)
        line = self._node % (name, attr_list)
        self.body.append(line)

    def edge(self, tail_name, head_name, label=None, _attributes=None, **attrs):
        """Create an edge between two nodes.

        Args:
            tail_name: Start node identifier
                (format: ``node[:port[:compass]]``).
            head_name: End node identifier
                (format: ``node[:port[:compass]]``).
            label: Caption to be displayed near the edge.
            attrs: Any additional edge attributes (must be strings).

        Note:
            The ``tail_name`` and ``head_name`` strings are separated
            by (optional) colon(s) into ``node`` name, ``port`` name,
            and ``compass`` (e.g. ``sw``).
            See :ref:`details in the User Guide <ports>`.
        """
        tail_name = self._quote_edge(tail_name)
        head_name = self._quote_edge(head_name)
        attr_list = self._attr_list(label, attrs, _attributes)
        line = self._edge % (tail_name, head_name, attr_list)
        self.body.append(line)

    def edges(self, tail_head_iter):
        """Create a bunch of edges.

        Args:
            tail_head_iter: Iterable of ``(tail_name, head_name)`` pairs
                (format:``node[:port[:compass]]``).


        Note:
            The ``tail_name`` and ``head_name`` strings are separated
            by (optional) colon(s) into ``node`` name, ``port`` name,
            and ``compass`` (e.g. ``sw``).
            See :ref:`details in the User Guide <ports>`.
        """
        edge = self._edge_plain
        quote = self._quote_edge
        lines = (edge % (quote(t), quote(h)) for t, h in tail_head_iter)
        self.body.extend(lines)

    def attr(self, kw=None, _attributes=None, **attrs):
        """Add a general or graph/node/edge attribute statement.

        Args:
            kw: Attributes target
                (``None`` or ``'graph'``, ``'node'``, ``'edge'``).
            attrs: Attributes to be set (must be strings, may be empty).

        See the :ref:`usage examples in the User Guide <attributes>`.
        """
        if kw is not None and kw.lower() not in ('graph', 'node', 'edge'):
            raise ValueError('attr statement must target graph, node, or edge:'
                             f' {kw!r}')
        if attrs or _attributes:
            if kw is None:
                a_list = self._a_list(None, attrs, _attributes)
                line = self._attr_plain % a_list
            else:
                attr_list = self._attr_list(None, attrs, _attributes)
                line = self._attr % (kw, attr_list)
            self.body.append(line)

    def subgraph(self, graph=None, name=None, comment=None,
                 graph_attr=None, node_attr=None, edge_attr=None, body=None):
        """Add the current content of the given sole ``graph`` argument
            as subgraph or return a context manager
            returning a new graph instance
            created with the given (``name``, ``comment``, etc.) arguments
            whose content is added as subgraph
            when leaving the context manager's ``with``-block.

        Args:
            graph: An instance of the same kind
                (:class:`.Graph`, :class:`.Digraph`) as the current graph
                (sole argument in non-with-block use).
            name: Subgraph name (``with``-block use).
            comment: Subgraph comment (``with``-block use).
            graph_attr: Subgraph-level attribute-value mapping
                (``with``-block use).
            node_attr: Node-level attribute-value mapping
                (``with``-block use).
            edge_attr: Edge-level attribute-value mapping
                (``with``-block use).
            body: Verbatim lines to add to the subgraph ``body``
                (``with``-block use).

        See the :ref:`usage examples in the User Guide <subgraphs>`.

        When used as a context manager, the returned new graph instance
        uses ``strict=None`` and the parent graph's values
        for ``directory``, ``format``, ``engine``, and ``encoding`` by default.

        Note:
            If the ``name`` of the subgraph begins with
            ``'cluster'`` (all lowercase)
            the layout engine will treat it as a special cluster subgraph.
        """
        if graph is None:
            return SubgraphContext(self, {'name': name,
                                          'comment': comment,
                                          'directory': self.directory,
                                          'format': self.format,
                                          'engine': self.engine,
                                          'encoding': self.encoding,
                                          'graph_attr': graph_attr,
                                          'node_attr': node_attr,
                                          'edge_attr': edge_attr,
                                          'body': body,
                                          'strict': None})

        args = [name, comment, graph_attr, node_attr, edge_attr, body]
        if not all(a is None for a in args):
            raise ValueError('graph must be sole argument of subgraph()')

        if graph.directed != self.directed:
            raise ValueError(f'{self!r} cannot add subgraph of different kind:'
                             f' {graph!r}')

        lines = ['\t' + line for line in graph.__iter__(subgraph=True)]
        self.body.extend(lines)


class SubgraphContext:
    """Return a blank instance of the parent and add as subgraph on exit."""

    def __init__(self, parent, kwargs):
        self.parent = parent
        self.graph = parent.__class__(**kwargs)

    def __enter__(self):
        return self.graph

    def __exit__(self, type_, value, traceback):
        if type_ is None:
            self.parent.subgraph(self.graph)
