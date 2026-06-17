# Challenge 2 — Cache Without Keeping Alive

**Time:** ~90 minutes. **Difficulty:** Medium.

## Problem

Design and implement a cache that:

1. Speeds up repeated lookups (the whole point).
2. Does NOT extend the lifetime of cached values beyond what the rest of the program needs.
3. Bounds memory (a hard limit you set).
4. Cleans up on eviction without leaving orphan objects.

Test it under three workloads and prove it doesn't leak.

## Acceptance criteria

A `notes/challenge-02-cache.py` containing your cache implementation with:

- [ ] A `BoundedWeakCache(max_size=N)` class that maps keys to weakly-referenced values.
- [ ] LRU eviction when full.
- [ ] Entries that vanish automatically when the underlying value is collected.
- [ ] A `peek(key)` method that returns the value WITHOUT marking it as recently-used (a common cache anti-pattern that pollutes LRU).
- [ ] A `stats()` method returning `(hits, misses, evictions, current_size)`.
- [ ] A pytest suite proving:
  - Cache hits after misses.
  - LRU eviction order.
  - Weakly-held values are reclaimed after the caller drops them.
  - Cache size never exceeds `max_size`.

## Three workloads to test against

1. **Workload A — small hot set.** 1000 lookups into 10 cached items. Hit rate should approach 100%. Memory should be bounded by `max_size`.
2. **Workload B — large unique stream.** 10,000 unique lookups. The cache should evict steadily; memory should remain bounded.
3. **Workload C — values dropped externally.** Insert 100 entries, then drop external references to half of them, then check `stats()`. The vanishing-on-collection behavior should reduce `current_size`.

## Hints

<details>
<summary>Why `WeakValueDictionary` alone isn't enough</summary>

It vanishes entries on collection (good) but doesn't enforce a max size (bad — under hot workloads, you may want to evict even still-live values to bound memory). You need to combine `OrderedDict` (for LRU) with weakref-aware deletion.

</details>

<details>
<summary>Skeleton</summary>

```python
import weakref
from collections import OrderedDict
from typing import Any, Hashable

class BoundedWeakCache:
    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._data: OrderedDict[Hashable, weakref.ReferenceType[Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: Hashable) -> Any | None:
        if key not in self._data:
            self._misses += 1
            return None
        value = self._data[key]()
        if value is None:
            # gc-collected; clean up
            del self._data[key]
            self._misses += 1
            return None
        self._hits += 1
        self._data.move_to_end(key)
        return value

    def put(self, key: Hashable, value: Any) -> None:
        self._data[key] = weakref.ref(value, lambda _r: self._on_collect(key))
        self._data.move_to_end(key)
        while len(self._data) > self._max_size:
            evicted_key, _ = self._data.popitem(last=False)
            self._evictions += 1

    def _on_collect(self, key: Hashable) -> None:
        self._data.pop(key, None)

    # peek + stats: implement yourself
```

The trick: `weakref.ref(value, callback)` lets you run a function when the value is collected. We use it to clean up our `OrderedDict` slot.

</details>

<details>
<summary>Testing the gc-collected behavior</summary>

```python
import gc

cache = BoundedWeakCache(max_size=10)

def make_value():
    v = MyValue()  # local — caller's only reference
    cache.put("k", v)
    return v        # caller now holds the only strong ref

v = make_value()
print(cache.stats())   # 1 entry
del v                  # drop the strong ref
gc.collect()           # trigger cleanup
print(cache.stats())   # 0 entries
```

</details>

## Stretch

- Add **time-based eviction** (entries expire after N seconds).
- Make the cache **thread-safe** with a `threading.Lock`. Benchmark vs without.
- Add a **size estimate** (using `sys.getsizeof` recursively or `pympler.asizeof`) and bound total bytes, not just count.

## Submission

Commit `challenge-02-cache.py` and `challenge-02-tests.py` to your portfolio under `c17-week-02/challenge-02/`.

## Why this matters

Almost every production Python system has a cache somewhere. Almost every one has a leak. Writing the leak-free version once installs the discipline; you'll recognize the antipatterns in code review for the rest of your career.
