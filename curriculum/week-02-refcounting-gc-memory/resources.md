# Week 2 — Resources

All free.

## Primary sources

- **CPython `Include/object.h`** — the `PyObject` and `PyVarObject` structs:
  <https://github.com/python/cpython/blob/main/Include/object.h>
- **CPython `Modules/gcmodule.c`** — the cyclic GC:
  <https://github.com/python/cpython/blob/main/Modules/gcmodule.c>
- **`gc` module docs**:
  <https://docs.python.org/3/library/gc.html>
- **`sys.getrefcount` docs**:
  <https://docs.python.org/3/library/sys.html#sys.getrefcount>
- **`weakref` module docs**:
  <https://docs.python.org/3/library/weakref.html>
- **`tracemalloc` docs**:
  <https://docs.python.org/3/library/tracemalloc.html>

## Tools

- **`memray`** — the modern memory profiler from Bloomberg, fully open-source. Produces flamegraphs:
  <https://github.com/bloomberg/memray>
  Install: `pip install memray`.
- **`objgraph`** — visualizes object reference chains:
  <https://github.com/mgedmin/objgraph>
  Install: `pip install objgraph`. Requires `graphviz` (`apt install graphviz` or `brew install graphviz`).
- **`pympler`** — alternative memory analyzer with summary tables:
  <https://github.com/pympler/pympler>

## Required PEPs

- **PEP 442 — Safe object finalization** (why Python 3 can collect cycles containing `__del__`):
  <https://peps.python.org/pep-0442/>
- **PEP 703 — Free-threaded CPython** (relevant for the refcounting story in 3.13+):
  <https://peps.python.org/pep-0703/>

## Free book chapters / write-ups

- **"Python's Garbage Collector" — A Look Inside CPython** by Artem Golubin:
  <https://rushter.com/blog/python-garbage-collector/>
- **"Memory management in Python" — Real Python (free article)**:
  <https://realpython.com/python-memory-management/>
- **Anthony Shaw's "CPython Internals" Real Python series — Memory management chapter (free)**:
  <https://realpython.com/cpython-internals-paperback/>

## CPython source map (the parts that matter this week)

| What | Where |
|------|-------|
| `PyObject` struct | `Include/object.h` |
| `Py_INCREF` / `Py_DECREF` macros | `Include/object.h` (look for `Py_INCREF`) |
| The cyclic GC's three generations | `Modules/gcmodule.c` |
| Small-int caching range (-5 to 256) | `Objects/longobject.c`, search `NSMALLPOSINTS` |
| String interning | `Objects/unicodeobject.c`, search `intern` |
| Object allocator (PyMalloc) | `Objects/obmalloc.c` |

## Glossary

| Term | Definition |
|------|------------|
| **PyObject** | The C struct underlying every Python object; contains refcount + type pointer + payload |
| **Refcount** | Integer counting how many references point at this object |
| **`Py_INCREF`** | C macro to bump a refcount (from C extensions) |
| **`Py_DECREF`** | C macro to decrement; frees the object at zero |
| **Reference cycle** | Two or more objects that reference each other; refcount alone can't free them |
| **Cyclic GC** | The "generational garbage collector" that finds and frees cycles |
| **Generation** | A bucket of objects by age. Gen 0 = young, Gen 2 = old. Young is collected more often. |
| **`__slots__`** | Class-level declaration of allowed attributes; replaces per-instance `__dict__` |
| **`weakref`** | A reference that doesn't bump the refcount |
| **`WeakValueDictionary`** | A dict whose values are weakly referenced; entries vanish when the value is collected |
| **`tracemalloc`** | Stdlib memory-allocation tracker |
| **`memray`** | A modern, open-source memory profiler |
| **`objgraph`** | A library to draw object reference chains |
| **Small-int caching** | CPython pre-allocates int objects -5 through 256 — they have shared identity |
| **Interning** | Two equal strings sharing one PyObject when the runtime knows it's safe |

---

*Broken link? Open an issue.*
