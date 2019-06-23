from __future__ import annotations
from typing import Mapping, Optional

import attr
import funcy as fn
from dfa import DFA

from lstar.common import Alphabet, Letter, LabelOracle, Word


@attr.s(auto_attribs=True)
class Node:
    data: Word
    children: Mapping[Letter, Optional[Node]] = attr.ib(factory=dict)

    @property
    def is_leaf(self):
        return len(self.children) == 0

    def __getitem__(self, key):
        return self.children.get(key)

    def __setitem__(self, key, val):
        self.children[key] = val


@attr.s(frozen=True, auto_attribs=True)
class ClassificationTree:
    alphabet: Alphabet = attr.ib(converter=frozenset)
    membership: LabelOracle
    root: Node = Node(())

    def _sift(self, word):
        node = self.root
        while not node.is_leaf:
            yield node
            test = word + node.data
            test_res = self.membership(test)

            if test_res not in node.children:  # Discovered new state.
                node[test_res] = Node(test)

            node = node[test_res]

        yield node

    def sift(self, word) -> Node:
        return fn.last(self._sift(word))

    def lca(self, word1, word2) -> Word:
        """Least Common Ancestor."""
        trace = zip(self._sift(word1), self._sift(word2))
        common_ancestors = (n1 for (n1, n2) in trace if n1 == n2)
        return fn.last(common_ancestors).data

    def extract_dfa(self) -> DFA:
        return DFA(
            start=(),
            alphabet=self.alphabet,
            accept=self.membership,
            transition=lambda w, c: self.sift(w + (c,)).data,
        )

    def update_tree(self, word: Word, hypothesis: DFA):
        if self.root.is_leaf:
            assert self.root.data == ()
            init_label = self.membership(())
            self.root[init_label] = Node(())
            self.root[not init_label] = Node(word)
            return

        sifts = map(self.sift, prefixes(word))
        trace = hypothesis.trace(word)

        prefix_prev = s_tree_prev = None
        for prefix, s_tree, s_cnd in zip(prefixes(word), sifts, trace):
            if s_tree.data != s_cnd:
                break

            prefix_prev, s_tree_prev = prefix, s_tree

        assert s_tree.data != s_cnd

        # TODO: can this membership query be inferred already
        #       from counter examples?
        # TODO: Only need to perform n-1 tests for moore machine.
        test = (prefix[-1],) + self.lca(s_tree.data, s_cnd)
        test_res = self.membership(s_tree_prev.data + test)

        s_tree_prev.children = {
            test_res: Node(s_tree_prev.data),
            (not test_res): Node(prefix_prev),
        }
        s_tree_prev.data = test


def prefixes(word):
    return (word[:i] for i in range(len(word) + 1))
