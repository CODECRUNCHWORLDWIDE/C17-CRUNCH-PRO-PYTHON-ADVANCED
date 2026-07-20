# C17 Diagnostic Quiz

25 questions. Score yourself honestly. Time limit: 60 minutes. No googling.

- **22–25:** You're ready. Start Week 1.
- **18–21:** You'll be challenged but you'll make it. Start Week 1.
- **14–17:** Possible to start C17, but you'll struggle from Week 4. Strongly recommend doing C16 Weeks 7–8 first.
- **<14:** Not ready yet. Finish C1, then C5 or C16.

---

**1.** What does `x is y` test, that `x == y` does not?

**2.** Given `def f(x=[]): x.append(1); return x`, what does `f()` return after being called three times in a row?

**3.** What is the time complexity of `list.append`, amortized? Worst case?

**4.** What does `__slots__` change about a class instance?

**5.** Why is `dict` ordered in Python 3.7+? (One sentence.)

**6.** What is the difference between `yield` and `yield from`?

**7.** In `try / except / else / finally`, when does `else` run?

**8.** What does `functools.lru_cache` do, and what's a case where it'd be wrong to use?

**9.** Write the smallest possible decorator that prints `"hello"` before the decorated function runs.

**10.** What does the `@staticmethod` decorator actually do, mechanically? (Not "what's it for" — "what does it produce.")

**11.** What is the MRO of `class D(B, C): ...` if `B` and `C` both inherit from `A`?

**12.** What's the difference between `__init__` and `__new__`?

**13.** What does the `@dataclass(frozen=True)` decorator give you?

**14.** What's a context manager protocol? Write a minimal one.

**15.** Explain what the `GIL` is in two sentences.

**16.** When is `multiprocessing` *worse* than `threading`?

**17.** Given `async def f(): return 1`, what does `f()` return? What about `await f()`?

**18.** What does `asyncio.run` do that you couldn't do with just `await`?

**19.** Why does `requests.get(...)` inside an async function harm performance?

**20.** In NumPy, what's the difference between `a.shape = (3, 4)` and `a.reshape(3, 4)`?

**21.** What does the `__slots__` mechanism cost you, in terms of features?

**22.** Run `dis.dis("x = 1; y = x + 2")`. Name two bytecodes you'd expect to see in the output.

**23.** What is a "weakref" and when would you use one?

**24.** What's the difference between `mypy` and `pyright`? (One sentence.)

**25.** A coworker says "Python doesn't have generics." How do you correct them in two sentences?

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. `is` tests *identity* (same object in memory, same `id()`). `==` tests *value equality* (whatever `__eq__` defines).
2. `[1]`, `[1, 1]`, `[1, 1, 1]`. The default value is a *shared* mutable list — created once at function-definition time. This is one of Python's most famous gotchas.
3. Amortized `O(1)`. Worst case `O(n)` when the list resizes (Python grows the underlying array geometrically).
4. It replaces the instance `__dict__` with a fixed C-array slot per declared attribute. Lower memory, faster attribute access, no per-instance attribute additions.
5. The hash table implementation now records insertion order. (Note: was a CPython implementation detail in 3.6; became part of the language spec in 3.7.)
6. `yield from iter` delegates to `iter`, forwarding values and `send/throw`. `yield iter` would yield the iterator object itself, not its values.
7. `else` runs only if the `try` block completed without raising.
8. Memoizes the return value of a function for given args. Wrong for: any function with side effects, any function whose args aren't hashable, any function whose result depends on time/state.
9.
```python
def hello(f):
    def wrapper(*a, **kw):
        print("hello")
        return f(*a, **kw)
    return wrapper
```
10. `@staticmethod` wraps the function in a `staticmethod` descriptor, which, when accessed via a class or instance, returns the function unchanged (no automatic `self`/`cls` injection).
11. `D → B → C → A → object` (C3 linearization).
12. `__new__` constructs the instance (returns it); `__init__` initializes it (receives the new instance via `self`). For immutable types like `tuple`, you override `__new__`.
13. An immutable dataclass: `__setattr__` and `__delattr__` raise. Also makes instances hashable (Python auto-generates `__hash__` for frozen dataclasses).
14.
```python
class Ctx:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False  # don't suppress
```
15. The Global Interpreter Lock prevents more than one thread from executing Python bytecode at once. It simplifies CPython's internals (refcounts in particular) but limits pure-Python multithreaded CPU work.
16. When the task is IO-bound (multiprocessing's overhead dominates), or when shared mutable state is needed (multiprocessing forces serialization), or on Windows where process startup is slow.
17. `f()` returns a coroutine object. `await f()` (inside another `async def`) runs it and yields the result, here `1`.
18. `asyncio.run` creates an event loop, runs the given coroutine to completion, cleans up, and closes the loop. You can't `await` outside a coroutine.
19. `requests` is blocking; calling it inside an async function freezes the entire event loop until it returns, preventing any other concurrent tasks from progressing.
20. `a.shape = (3, 4)` modifies `a` in place (must be compatible with size). `a.reshape(3, 4)` returns a new view (or copy if memory layout doesn't permit a view).
21. No `__dict__`, no `__weakref__` (unless declared), no adding new attributes at runtime, awkwardness with multiple inheritance.
22. Likely: `LOAD_CONST`, `STORE_NAME` (or `STORE_FAST`), `BINARY_OP` (3.11+) or `BINARY_ADD` (pre-3.11), `RETURN_VALUE`. Exact bytecodes vary by Python version.
23. A reference to an object that doesn't prevent it from being garbage collected. Used for caches and callbacks where you don't want to extend an object's lifetime.
24. `mypy` is the original type checker, written by the people who designed Python's type system. `pyright` is Microsoft's faster, stricter alternative used inside VS Code's Pylance.
25. Python has supported generics since PEP 484 (3.5). Use `TypeVar` and `Generic[T]`, or in 3.12+ the `class Foo[T]: ...` syntax. They are *runtime-erased* (mostly) but enforced by type checkers.

</details>

---

If you got many questions wrong but want to push through anyway — be honest with yourself. C17 doesn't slow down. Mid-Week-4 stress is much higher than the stress of doing one more month of C16.
