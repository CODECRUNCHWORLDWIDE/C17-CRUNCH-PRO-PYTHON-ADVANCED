"""
Exercise 2 — Build a cycle, detect it, break it.

Goal: construct a reference cycle, verify it's NOT freed by refcounting,
trigger the GC to collect it, then redesign so refcounting alone is enough.

Estimated time: 30 minutes.

Run with: python exercise-02-build-a-cycle.py

Acceptance:
- You walk through each STAGE and observe what gc.collect() reports.
- You can explain why Stage 2 (weakref) does NOT require gc.collect().
- Your reflections committed to `notes/exercise-02.md`.
"""

from __future__ import annotations

import gc
import sys
import weakref


# ----- STAGE 1 — build a cycle the naive way -----------------------------


class Node:
    def __init__(self, name: str) -> None:
        self.name = name
        self.peer: "Node | None" = None

    def __repr__(self) -> str:
        return f"<Node {self.name}>"


def stage_1_cycle() -> None:
    """Two nodes referencing each other. Refcount alone cannot free them."""
    print("=" * 60)
    print("STAGE 1 — naive cycle")
    print("=" * 60)

    a = Node("a")
    b = Node("b")
    a.peer = b
    b.peer = a

    # At this point: a.refcount = 2 (variable + b.peer), b.refcount = 2.
    print(f"After creation: a.refcount = {sys.getrefcount(a) - 1}")
    print(f"                b.refcount = {sys.getrefcount(b) - 1}")

    # Disable GC so we can see the leak with our own eyes.
    gc.disable()

    # Note the count of Node instances before we del.
    before = len([o for o in gc.get_objects() if isinstance(o, Node)])

    del a, b

    after_del = len([o for o in gc.get_objects() if isinstance(o, Node)])
    print(f"Live Nodes before del:    {before}")
    print(f"Live Nodes after del:     {after_del}")
    print("If after_del == 2, the cycle did NOT collect via refcount.")

    # Now run the GC manually.
    collected = gc.collect()
    after_gc = len([o for o in gc.get_objects() if isinstance(o, Node)])
    print(f"gc.collect() returned:    {collected}")
    print(f"Live Nodes after GC:      {after_gc}")
    print("Expect: after_gc == 0 (or initial).")

    gc.enable()


# ----- STAGE 2 — break the cycle with weakref ---------------------------


class WeakNode:
    def __init__(self, name: str) -> None:
        self.name = name
        # Note: hold peer weakly. The other node must own a strong reference
        # via some other path (e.g., a parent collection) for both to be reachable.
        self._peer_ref: weakref.ref[WeakNode] | None = None

    @property
    def peer(self) -> "WeakNode | None":
        if self._peer_ref is None:
            return None
        return self._peer_ref()

    @peer.setter
    def peer(self, value: "WeakNode | None") -> None:
        self._peer_ref = weakref.ref(value) if value is not None else None

    def __repr__(self) -> str:
        return f"<WeakNode {self.name}>"


def stage_2_weakref() -> None:
    """Same shape but peer is a weakref. Refcounting alone is enough."""
    print()
    print("=" * 60)
    print("STAGE 2 — peer held weakly")
    print("=" * 60)

    a = WeakNode("a")
    b = WeakNode("b")
    a.peer = b
    b.peer = a

    print(f"After creation: a.refcount = {sys.getrefcount(a) - 1}")
    print(f"                b.refcount = {sys.getrefcount(b) - 1}")
    print("(Both 1 — weakrefs don't bump refcounts.)")

    # Disable GC so we observe pure refcount behavior.
    gc.disable()

    before = len([o for o in gc.get_objects() if isinstance(o, WeakNode)])
    del a, b
    after_del = len([o for o in gc.get_objects() if isinstance(o, WeakNode)])
    print(f"Live WeakNodes before del: {before}")
    print(f"Live WeakNodes after del:  {after_del}")
    print("Expect: after_del == 0 — refcount alone freed them.")

    gc.enable()


# ----- STAGE 3 — a closure-captures-self cycle ---------------------------


class Server:
    def __init__(self, name: str) -> None:
        self.name = name
        # This callback's closure captures `self`. Cycle!
        self.callback = lambda: self.handle()

    def handle(self) -> None:
        pass

    def __repr__(self) -> str:
        return f"<Server {self.name}>"


def stage_3_closure_cycle() -> None:
    print()
    print("=" * 60)
    print("STAGE 3 — lambda closure captures self")
    print("=" * 60)

    s = Server("api")
    print(f"After creation: s.refcount = {sys.getrefcount(s) - 1}")
    print("Greater than 1 even though only `s` references it directly.")

    gc.disable()
    before = len([o for o in gc.get_objects() if isinstance(o, Server)])
    del s
    after_del = len([o for o in gc.get_objects() if isinstance(o, Server)])
    print(f"Live Servers before del:   {before}")
    print(f"Live Servers after del:    {after_del}")
    print("Expect: after_del still > 0 — closure pinned it.")

    collected = gc.collect()
    after_gc = len([o for o in gc.get_objects() if isinstance(o, Server)])
    print(f"gc.collect() collected:    {collected}")
    print(f"Live Servers after GC:     {after_gc}")
    print("Expect: after_gc == 0.")
    gc.enable()


# ----- entry point -------------------------------------------------------


def main() -> None:
    stage_1_cycle()
    stage_2_weakref()
    stage_3_closure_cycle()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# REFLECTION
# -----------------------------------------------------------------------------
# 1. In Stage 2, neither node owns the other. What keeps the dangling weakref
#    from being a footgun?  Answer: weakref() returns None if the target is
#    gone. Always check before use.
#
# 2. Stage 3 demonstrates a cycle from a lambda. How would you re-design
#    `Server` to avoid it? Hint: bind `self.handle` directly (method bound
#    to instance) instead of wrapping in a lambda. Bound methods also hold
#    a reference to self, but most lifecycles tolerate this. Or store the
#    callback as a free function that takes `self` as arg.
#
# 3. Build a fourth scenario yourself: an "Observer pattern" where a Subject
#    holds a list of Observers and each Observer holds a back-reference to
#    its Subject. Where's the cycle? Apply the weakref fix to one side.
# -----------------------------------------------------------------------------
