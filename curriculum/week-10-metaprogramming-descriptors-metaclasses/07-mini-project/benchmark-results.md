# Benchmark results — reference run

> *Read after you have run `benchmark.py` on your own machine and produced your own results. Comparing yours against these is a calibration exercise; the absolute numbers will differ across machines (CPython version, CPU, memory pressure, OS) but the *ordering* should be roughly stable. If yours differs in ordering, that is worth investigating.*

## The reference machine

The numbers below were captured on:

- Apple Silicon (M-class CPU; arm64)
- macOS 14+ (Darwin 25)
- CPython 3.13.x
- No competing CPU load
- `tracemalloc` warm-up done before the timed run

Your absolute numbers will shift by a factor of 0.7x to 1.5x on different machines; the ordering ("Decorator is comparable to InitSubclass, Descriptor is slightly slower on set, Metaclass is comparable to Decorator") should hold.

## The numbers

```text
metric                         Decorator   InitSubcls  Descriptor   Metaclass
----------------------------------------------------------------------------
instance create (microsec)         1.2          1.2          1.1         1.1
attribute set (microsec)           0.03         0.03         0.26        0.03
bytes per instance               212          212          212         212
```

Memory per instance is functionally identical (~210 bytes including the Python object header, two slots for `name` and `age`, and the `__dict__` overhead). The differences fall well within `tracemalloc`'s precision.

Instance creation is comparable across the four mechanisms. The Descriptor and Metaclass versions are slightly faster on this machine because their `__init__` does less work (the Decorator and InitSubclass versions both walk a spec dict; the Descriptor routes through `__set__` which is a single C call per attribute; the Metaclass version is the same as InitSubclass except the dispatch is one hop shorter). The differences are tens of nanoseconds. Below noise for any application that is not creating tens of millions of instances per second.

Attribute set is where the Descriptor version pays a real cost — about 10x slower than the other three. The cost is the Python-level `__set__` call (versus the other three's direct `instance.__dict__` write). 0.26 microseconds is still about four million writes per second on this machine. For most workloads this is irrelevant. For an inner loop that mutates instance attributes millions of times per second (rare; a profiler will tell you), the Descriptor version's `__set__` becomes the bottleneck and you would either:

- Move the descriptor's validation logic to a C extension (Cython or a real C extension; Week 8 material).
- Skip the descriptor and write directly to `instance.__dict__` via a class decorator that generates inline-validation `__init__` plus plain attribute storage.

The first is heavy. The second is the path `dataclasses` takes; it is a real argument for the class decorator approach over descriptors when raw attribute-set throughput is on the critical path.

## What the numbers do not show

Three costs do not appear in the benchmark and they matter more than the timing differences.

**Cost 1: type-checker friction.** The Metaclass implementation, run through `mypy` and `pyright`, fails to recognise that `UserMetaclass(name="alice", age=30)` should be a valid call. The other three implementations type-check correctly out of the box (Decorator and InitSubclass benefit from explicit annotations; Descriptor benefits because `StringField` has typed `__get__`/`__set__`). To make the Metaclass version cooperate, you need either `@typing.dataclass_transform()` (PEP 681), a mypy plugin, or `.pyi` stubs. None of these is free.

**Cost 2: cooperation with multiple inheritance.** The Metaclass version introduces a metaclass conflict any time the user wants to mix `ModelMetaclass`-derived classes with another metaclass-using class (`abc.ABC`, an `enum.Enum`, a `typing.Protocol`). The user has to manually construct a combined metaclass. The other three versions have no such constraint.

**Cost 3: cognitive load.** The Decorator version reads like a function. The InitSubclass version reads like ordinary inheritance. The Descriptor version reads like a small ORM. The Metaclass version reads like dark magic. For a teammate reading the code in two years, the cognitive cost of the Metaclass version is real and unmeasured.

## Recommendation, ordered by frequency of correct choice

For the validated-model use case as specified:

1. **InitSubclass** (`ModelInitSubclass`) is the right default. Natural inheritance, no metaclass conflict, no decorator-application-on-subclasses problem.
2. **Descriptor** (`ModelDescriptor`) is the right answer when fields need their own behaviour beyond per-instance validation (caching, computed values, ORM-style persistence).
3. **Decorator** (`@validated_model`) is the right answer when the consumer wants to mark specific classes for the transformation (`@dataclass`-style) and inheritance is not part of the use case.
4. **Metaclass** (`ModelMetaclass`) is the right answer in this specific use case approximately never. The use case (validated models with declarative fields) is exactly what PEP 487 removed the need for a metaclass for.

The benchmark numbers do not, by themselves, tell you which mechanism to pick. The decision tree does. The benchmark exists to confirm that the performance differences are not the dominant factor — which they almost never are.

## Variability across Python versions

CPython has shaved descriptor `__set__` overhead in 3.11 and 3.12 via specialised bytecode. Your numbers on 3.10 versus 3.13 will differ by roughly 20–30% on the attribute-set row. The InitSubclass and Decorator rows are roughly stable across versions. The Metaclass row's instance-creation time has improved modestly in 3.13 (the metaclass `__call__` is specialised in some cases).

If you re-run this benchmark on PyPy, expect a 5–10x improvement across the board for the InitSubclass and Decorator versions; the Descriptor version improves less (PyPy's JIT does not optimise Python-level `__set__` as aggressively as plain attribute writes). PyPy under the same workload would shift the calculus: the Descriptor version's attribute-set cost would still be the highest of the four, just less catastrophically so.

## Variability across workload

The benchmark assumes 2-field models. For 20-field models, the Decorator and InitSubclass `__init__` (which loop over the field list) scale linearly with field count. The Descriptor version's `__init__` also loops (over `_fields`), so it scales the same. The Metaclass version is the same.

The interesting non-linearity is in *class creation*, not measured in this benchmark. The Metaclass `__new__` runs once per class definition; if you define hundreds of model classes, the per-class overhead accumulates. This is a real cost in Django-scale applications. The Decorator's `__init__` synthesis takes about the same time per class, so the cost is similar. InitSubclass and Descriptor have negligible per-class overhead. *None* of these matters unless you are defining classes dynamically in a hot path.

## Conclusion

The dominant factor in choosing among the four mechanisms is not performance. It is **fit to the problem shape**: who owns the class, what the field declarations need to express, how subclassing should behave, and how the type checker should understand the result. The benchmark numbers are within a factor of 2x for instance creation and a factor of 10x for the worst case of attribute set. **For applications below a million attribute-sets per second on the hot path — almost all applications — the performance differences are not the right axis of decision.**
