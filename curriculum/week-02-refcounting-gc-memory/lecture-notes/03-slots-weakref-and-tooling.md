# Lecture 3 — `__slots__`, `weakref`, and the Tooling Tour

> **Duration:** ~2 hours. **Outcome:** You can apply `__slots__` correctly to reduce memory, use `weakref` to prevent unintentional retention, and run `tracemalloc` / `memray` / `objgraph` against a real program.

## 1. `__slots__` — what it does

A normal Python instance has a `__dict__` for its attributes:

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
p.__dict__   # {'x': 1, 'y': 2}
p.color = "red"  # works — dynamic attributes
```

The `__dict__` is a hash table. For ten million `Point` instances, that's ten million hash tables, each occupying maybe 100-300 bytes.

`__slots__` replaces the `__dict__` with a fixed-size array:

```python
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
p.x          # 1
p.color = "red"  # AttributeError!
```

The instance now occupies just enough memory for `x` and `y` — maybe 50 bytes. For ten million `Point` instances, that's 500 MB instead of 1-3 GB.

## 2. What `__slots__` costs you

You give up:

- **Dynamic attributes.** Can't add new ones at runtime.
- **`__dict__`.** Code that introspects via `instance.__dict__` breaks.
- **`__weakref__`.** Unless you add `"__weakref__"` to `__slots__` explicitly, `weakref.ref(instance)` raises.
- **Multiple inheritance from non-slotted bases** in some cases. Mixing slotted and non-slotted bases is subtle.

Practical rule: use `__slots__` for **data-heavy classes that have many instances** (geometric primitives, event objects, log records). Don't use it on classes that are intentionally extensible.

## 3. Measuring the win

```python
import sys

class Regular:
    def __init__(self):
        self.x = 1
        self.y = 2

class Slotted:
    __slots__ = ("x", "y")
    def __init__(self):
        self.x = 1
        self.y = 2

print(sys.getsizeof(Regular()))   # ~ 48 bytes, but the __dict__ is extra:
print(sys.getsizeof(Regular().__dict__))  # ~ 296 bytes — the real cost

print(sys.getsizeof(Slotted()))   # ~ 48 bytes total — no __dict__
```

Note: `sys.getsizeof` only reports the object itself, not what it points at. For a regular class, you also pay for the `__dict__`. For a slotted class, you don't.

Exercise 3 walks through this measurement against `pympler.asizeof` (which recurses).

## 4. `dataclass(slots=True)` — the modern shortcut

Python 3.10+:

```python
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float
```

This gives you `__slots__`, `__init__`, `__repr__`, `__eq__`, `__hash__` (because frozen), `__match_args__` — all generated. Production-quality value types in one decorator.

## 5. `weakref` — the reference that doesn't count

A normal reference increments the refcount. A `weakref` does not.

```python
import weakref

class Obj:
    pass

o = Obj()
ref = weakref.ref(o)
print(ref())              # <Obj ...>  — the weakref dereferences to the object
del o
print(ref())              # None — the object is gone
```

`weakref.ref(obj)` returns a callable. Calling it gives you the object (if still alive) or `None`. The weakref does not extend the object's lifetime.

**Caveat:** not every object can have a weakref. Specifically, built-in types like `list`, `dict`, `tuple`, `int`, `str` do not (by default) support weakrefs. Your own classes do (unless you `__slots__` without `"__weakref__"`).

### `WeakValueDictionary`

The canonical use case: a cache where you don't want to extend the lifetime of cached values.

```python
import weakref

cache = weakref.WeakValueDictionary()

class Image:
    def __init__(self, path):
        self.path = path

def get_image(path):
    if path not in cache:
        cache[path] = Image(path)
    return cache[path]

img = get_image("foo.png")
# cache contains "foo.png" -> <Image>
del img
# Now nothing else references the Image. Eventually the entry in cache disappears.
```

The cache speeds up lookups without preventing collection. When the last "real" reference is dropped, the cache entry vanishes on its own.

### `WeakKeyDictionary`

The mirror image: keys are weakly referenced. Use case: associating data with objects without preventing those objects' collection.

```python
import weakref

# Attach a "log" to each request object without keeping requests alive
request_logs = weakref.WeakKeyDictionary()
request_logs[request] = []
```

## 6. `tracemalloc` — the stdlib tracer

```python
import tracemalloc
tracemalloc.start()

# ... your code that may leak ...

snapshot1 = tracemalloc.take_snapshot()

# ... more code, after which we suspect a leak ...

snapshot2 = tracemalloc.take_snapshot()

# Compare
top_stats = snapshot2.compare_to(snapshot1, "lineno")
for stat in top_stats[:10]:
    print(stat)
```

Output looks like:

```
/path/to/your/module.py:42: size=12.3 MiB (+12.3 MiB), count=1000 (+1000), average=12.6 KiB
```

That tells you exactly which source line is allocating memory that didn't get freed.

**Cost:** `tracemalloc` slows your program ~2x and uses extra memory itself. Don't leave it on in production; turn it on locally when hunting.

## 7. `memray` — the modern profiler

```bash
pip install memray
memray run my_script.py
memray flamegraph memray-my_script.bin
```

This produces an interactive flamegraph in an HTML file. You can:

- See the call tree of allocations.
- Filter by allocator (Python vs C).
- See peak memory vs total allocated.
- Run with `--trace-python-allocators` to get per-Python-line attribution.

`memray` is what you reach for first in 2026 for real memory profiling. Free and open-source (Bloomberg).

For long-running programs:

```bash
memray run -o memray.bin --live my_server.py
# In another terminal:
memray live <pid>
```

## 8. `objgraph` — drawing the reference chain

When you know an object is leaking but can't figure out who's holding it:

```python
import objgraph

# What types have the most live instances?
objgraph.show_most_common_types(limit=10)

# Draw a backref chain from a specific object
import gc
objs = [o for o in gc.get_objects() if isinstance(o, MyClass)]
objgraph.show_backrefs(objs[:3], filename="leak.png", max_depth=5)
```

This produces a PNG you can open and visually inspect. Shows which objects reference which, all the way back to a global / module root / frame.

Requires `graphviz` installed on the system.

## 9. The leak-hunting playbook

When you suspect a leak:

1. **Reproduce locally with a smaller workload.** Make it as deterministic as possible.
2. **Take a `tracemalloc` snapshot, run the leaky workload, take another, `compare_to`.** The top line is usually the culprit's source line.
3. **If `tracemalloc` is ambiguous, switch to `memray`.** The flamegraph attribution is richer.
4. **If you know the object type but not the holder, use `objgraph.show_backrefs`.** Visualize who's pinning it.
5. **Fix.** Common fixes: bound the cache (`functools.lru_cache(maxsize=N)`), use `weakref` for back-pointers, close generators, clear long-lived module-level lists.
6. **Verify.** Re-run the snapshot comparison. The line that was leaking should now be flat.

## 10. The 3.13 free-threaded caveat for memory

In free-threaded CPython (PEP 703), allocators behave slightly differently. Most user code doesn't notice. If you write a high-allocation library, test on both builds — the perf characteristics differ.

## 11. Self-check

- For what kind of class is `__slots__` a clear win? When would you NOT use it?
- Write a 3-line snippet that uses `WeakValueDictionary` as a cache.
- `tracemalloc.compare_to` returns what kind of objects? What's the most useful field?
- A list at module level grows by 100 items per request. Which leak pattern is this? How do you fix it?
- Generators can leak their captured state. Why?

## Further reading

- **`weakref` module docs**: <https://docs.python.org/3/library/weakref.html>
- **`memray` docs**: <https://bloomberg.github.io/memray/>
- **`objgraph` docs**: <https://mg.pov.lt/objgraph/>
- **Anthony Shaw — "How CPython Manages Memory" (free Real Python series)**: <https://realpython.com/cpython-internals-paperback/>

When all three lectures are clear, the [exercises](../exercises/README.md) drill the tooling.
