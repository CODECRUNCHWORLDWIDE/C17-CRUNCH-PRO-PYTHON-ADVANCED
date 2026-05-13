# Lecture 2 — Cycles and the Generational GC

> **Duration:** ~2 hours. **Outcome:** You can construct a reference cycle in three lines of Python, explain why refcounting alone can't free it, and describe how the generational GC works in three sentences.

## 1. The problem refcounting can't solve

Refcounting works perfectly when references form a **tree**: parent owns child; when parent goes away, parent's `DECREF` cascades down. The whole tree is freed.

It fails when references form a **cycle**:

```python
a = []
b = []
a.append(b)
b.append(a)

# Now a and b reference each other. Refcount of each: 2 (one for the variable, one from the other list).

del a
del b
```

After `del a; del b`:

- `a`'s variable binding is gone, refcount drops from 2 → 1 (only `b` still references it).
- `b`'s variable binding is gone, refcount drops from 2 → 1 (only `a` still references it).

Neither hits zero. Both are unreachable from your code, but neither can free the other without first hitting zero.

**Without a cycle collector, this is a memory leak.** CPython's solution: a separate garbage collector that runs periodically and finds these "islands" of unreachable cycles.

## 2. The generational garbage collector

CPython's GC is **generational**. Objects are sorted into three generations: 0 (youngest), 1, 2 (oldest).

```python
import gc
print(gc.get_threshold())  # (700, 10, 10) by default
```

Read that as: "Run a Gen 0 collection after every 700 new allocations. Run Gen 1 after every 10 Gen 0 cycles. Run Gen 2 after every 10 Gen 1 cycles."

**Why generations?** Empirical observation (the *generational hypothesis*): most objects die young. So checking Gen 0 frequently catches most garbage with little work; checking Gen 2 rarely is fine because old objects are usually still alive.

**The algorithm** (simplified):

1. For each container object (`list`, `dict`, `set`, instance with `__dict__`, etc.), CPython tracks it in the GC's lists when it's created.
2. When a generation triggers, the GC walks every tracked object in that generation.
3. For each, it counts "internal references" (references from other tracked objects).
4. It compares against the actual refcount.
5. If `internal_references == refcount`, this object is only kept alive by other tracked objects — i.e., it's part of a cycle.
6. Such objects are collected.
7. Surviving objects get promoted to the next generation (under the theory that older objects tend to live longer).

Non-container types (int, str, float, bytes, tuple-of-immutables) cannot form cycles, so they're not tracked. They're freed by refcount alone.

## 3. Looking at the GC from Python

```python
import gc

# Current counts per generation
print(gc.get_count())                  # (e.g., 432, 5, 2)

# What thresholds trigger each generation
print(gc.get_threshold())              # (700, 10, 10)

# Force a full collection
collected = gc.collect()
print(collected, "objects collected")

# All objects the GC tracks
gc.get_objects()                       # huge list; don't print

# What references this object?
gc.get_referrers(some_object)          # who holds it

# What does this object reference?
gc.get_referents(some_object)          # what it holds
```

`gc.get_referrers` is the diagnostic tool of last resort. When you can't figure out what's keeping an object alive, this answers.

## 4. The canonical cycle-detector exercise

```python
import gc

class Node:
    def __init__(self):
        self.peer = None

a = Node()
b = Node()
a.peer = b
b.peer = a

# Disable the GC temporarily to make the leak visible
gc.disable()
del a, b

# The two Node instances are unreachable but not yet collected
print(len([o for o in gc.get_objects() if isinstance(o, Node)]))
# → 2

# Now re-enable and run a manual collection
gc.enable()
collected = gc.collect()
print(collected)                        # → ≥2 (the two nodes + maybe their dicts)
print(len([o for o in gc.get_objects() if isinstance(o, Node)]))
# → 0
```

This is the GC doing exactly what refcounting could not.

## 5. The `__del__` finalizer problem (resolved in 3.4+)

Historical wart: in Python 2, the GC could not collect cycles containing objects with `__del__` methods. The reason: the GC didn't know what order to call the finalizers in. So those cycles were placed in `gc.garbage` — a list of "things we found but can't free."

Python 3.4 (via PEP 442) fixed this: cycle-aware finalization, where `__del__` is called *before* the cycle is broken, with the cycle still walkable. So `__del__` in cycles works correctly now.

You still should avoid relying on `__del__`. But it's no longer a leak source.

## 6. Common cycle patterns to recognize

### A. Parent-child with mutual reference

```python
class Parent:
    def __init__(self):
        self.children = []

class Child:
    def __init__(self, parent):
        self.parent = parent
        parent.children.append(self)
```

Every `Parent` holds its `Child`s; every `Child` holds its `Parent`. Cycle. Fix: use `weakref` on the child's `parent` reference.

### B. Closure capturing self

```python
class Server:
    def __init__(self):
        self.callback = lambda: self.handle()  # captures self
    def handle(self):
        pass
```

The lambda's closure holds `self`. `self` holds the callback. Cycle.

### C. Generator pinning frame state

```python
def gen():
    state = {"large": [0] * 10_000_000}
    yield 1
    yield state

g = gen()
next(g)
# At this point, the generator has yielded 1 and is paused.
# It still holds the frame, which still holds `state` with 10M ints.
```

`state` is alive as long as `g` is. If `g` outlives its usefulness, the memory leaks. Fix: exhaust the generator (or `g.close()`) when done.

### D. Lru_cache holding large args forever

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def compute(x):
    return x * 2

compute(big_object)  # big_object is now permanently retained by the cache
```

`maxsize=None` is a footgun. Use a bounded cache. Or `functools.lru_cache(maxsize=128)`.

## 7. `gc.set_debug` for live tracing

```python
import gc
gc.set_debug(gc.DEBUG_LEAK)

# Now every collection prints what it found
gc.collect()
```

`DEBUG_LEAK` puts unreachable objects into `gc.garbage` instead of freeing them, so you can inspect what would have been collected. Useful during leak hunts. **Don't leave it on in production.**

## 8. When to disable the GC

Almost never. But the canonical case: bulk loading. If you're constructing millions of objects in a tight loop, the GC may trigger spurious collections that slow you down (the objects you're creating aren't cycles; they don't need collecting). The pattern:

```python
import gc

gc.disable()
try:
    for record in giant_dataset:
        objects.append(parse(record))
finally:
    gc.enable()
    gc.collect()
```

Measure first. Many "obvious" disable-the-GC wins disappear under benchmarking.

## 9. Self-check

- Sketch a 3-line cycle and explain why each object's refcount stays > 0 after both names are deleted.
- Why does CPython's GC have three generations specifically?
- Which built-in types are NOT tracked by the GC, and why?
- `gc.get_referrers(obj)` — what does it return? When is it useful?
- A method `Parent.add(child)` makes `parent.children` hold `child` and `child.parent = self`. Where's the cycle? How would you fix it with `weakref`?

## Further reading

- **PEP 442 — Safe object finalization**: <https://peps.python.org/pep-0442/>
- **Artem Golubin — "Python's Garbage Collector"**: <https://rushter.com/blog/python-garbage-collector/>
- **CPython `Modules/gcmodule.c`** — read the top doc-comment for the algorithm in plain English:
  <https://github.com/python/cpython/blob/main/Modules/gcmodule.c>
