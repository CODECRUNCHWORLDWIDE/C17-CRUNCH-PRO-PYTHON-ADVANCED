# Week 2 — Quiz

Ten questions. Lectures closed.

---

**Q1.** Every PyObject contains, at minimum:

- A) A name string and a type pointer.
- B) A reference count and a type pointer.
- C) A reference count and a hash value.
- D) A type pointer and a payload size.

<details>
<summary>Answer</summary>

**B** — refcount + type pointer (then payload, which varies).

</details>

---

**Q2.** `sys.getrefcount(x)` reports a count of 3 immediately after `x = []`. What's the "real" count?

- A) 0
- B) 1 — `getrefcount`'s own argument bumped it by 1, then there's the `x` binding (1), then 1 more from… something. Wait — this is wrong.
- C) 2 — the `x` binding plus `getrefcount`'s argument.
- D) 3 — exactly as reported.

(Re-read the options carefully.)

<details>
<summary>Answer</summary>

**C** — real count is 2: the `x` binding plus `getrefcount`'s argument. The reported value is 3.

</details>

---

**Q3.** Why is `gc.collect()` needed at all, given refcounting?

- A) Refcounting is slow; the GC is faster.
- B) Refcounting cannot reclaim cyclic garbage.
- C) The GC handles freeing memory the refcounter can't see.
- D) Both B and C are essentially the same answer.

<details>
<summary>Answer</summary>

**D** — both B and C are saying the same thing. The technical answer is B; C is the casual phrasing.

</details>

---

**Q4.** Adding `__slots__ = ("x", "y")` to a class:

- A) Has no effect; `__slots__` is deprecated.
- B) Replaces the instance `__dict__` with fixed slots — saves memory, prevents adding new attributes.
- C) Adds runtime type-checking on `x` and `y`.
- D) Makes the class immutable.

<details>
<summary>Answer</summary>

**B** — replaces `__dict__` with fixed slots. Memory win; loss of dynamic attributes.

</details>

---

**Q5.** `weakref.ref(obj)`:

- A) Returns a callable that yields `obj` if still alive, else `None`.
- B) Returns a tuple containing `obj` and its refcount.
- C) Increments the refcount of `obj` but doesn't store a strong reference.
- D) Deletes the object immediately.

<details>
<summary>Answer</summary>

**A** — callable returning the object or `None`. Refcount is NOT incremented.

</details>

---

**Q6.** Which type CANNOT have a weakref taken of it by default?

- A) A user-defined class without `__slots__`.
- B) A `list`.
- C) A `Server` class with `__slots__ = ("name",)`.
- D) Both B and C.

<details>
<summary>Answer</summary>

**D** — both. `list` doesn't support weakref; `__slots__` without `"__weakref__"` removes the support.

</details>

---

**Q7.** CPython's cyclic GC has three generations because:

- A) Most objects die young; checking young objects frequently catches most garbage.
- B) Three is a tunable parameter; modern CPython actually has more.
- C) The first version had three; backwards compatibility forces it.
- D) Each generation maps to a thread.

<details>
<summary>Answer</summary>

**A** — generational hypothesis: most objects die young.

</details>

---

**Q8.** `tracemalloc.snapshot.compare_to(earlier, "lineno")` returns:

- A) A list of files with size changes.
- B) A list of statistics per source line, sorted by size difference.
- C) The total memory difference as an integer.
- D) Nothing — it prints and returns None.

<details>
<summary>Answer</summary>

**B** — list of statistics per source line, sorted by size difference.

</details>

---

**Q9.** A leak symptom: a global `cache = {}` grows unboundedly across requests. The fix is:

- A) Replace with `WeakValueDictionary` if values have other strong holders.
- B) Replace with `functools.lru_cache(maxsize=128)` if values are derived from the args.
- C) Add manual `cache.clear()` at scheduled intervals.
- D) Any of A, B, or C, depending on the access pattern.

<details>
<summary>Answer</summary>

**D** — depends on the pattern. All three are valid in different scenarios.

</details>

---

**Q10.** The 3.13 free-threaded build's main change to refcounting is:

- A) Refcounts are removed entirely; only the cyclic GC runs.
- B) Biased reference counting — each object has an owner thread that uses fast non-atomic ops.
- C) Refcounts are signed 64-bit integers (used to be 32-bit).
- D) Refcounts are stored in a side table, not on the object.

<details>
<summary>Answer</summary>

**B** — biased reference counting (PEP 703).

</details>

If 9+: ship homework. 7-8: re-read Lecture 1 and 3. <7: re-read all three lectures.

---
