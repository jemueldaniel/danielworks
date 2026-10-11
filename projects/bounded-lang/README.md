# Bounded language pipeline

A small, dependency-free Rust language implementation: lexer → precedence parser → AST → name-resolved stack IR → VM. This is original AI-assisted showcase code, not a copy of a private compiler.

## Reproduce

Run from the repository root with an installed Rust toolchain supporting edition 2024:

```sh
cargo test --manifest-path projects/bounded-lang/Cargo.toml --locked --offline
cargo fmt --manifest-path projects/bounded-lang/Cargo.toml -- --check
cargo clippy --manifest-path projects/bounded-lang/Cargo.toml --locked --offline --all-targets -- -D warnings
```

The package has no third-party dependencies and its Cargo lock is included. The latest Windows run passed **18 tests**, formatting and clippy. Earlier provenance records name cargo/rustc 1.95.0; a fresh version-query preflight was blocked, so that version is not represented as freshly verified. No Linux Rust execution is claimed.

## Execution and binding semantics

```text
let x = 2 + 3 * 4;
return x - 5;
→ 9
```

Each `let` allocates a new local slot. A later declaration shadows the previous visible name; its initializer resolves against the earlier environment. Later unrelated declarations cannot alias that shadowed slot:

```text
let x = 1;
let x = x + 1;
let y = 7;
return x + y;
→ 9
```

The regression was run against the old implementation first: repeated `x` failed with `UnknownName`, and the second program returned `14`. A separate regression exposed a local-count wrap at 65,536 bindings. All original tests remain intact. The corrected compiler separates total bindings from visible-name count and uses checked allocation; it supports at most 65,535 local slots.

## Explicit bounds and errors

Compilation rejects input larger than **1,048,576 UTF-8 bytes** and statements containing more than **256 tokens** (excluding the semicolon). These checks run before the recursive parser/emitter. They bound both nested parentheses and flat expression trees. Oversized input yields `CompileLimit`; malformed syntax yields `Parse` or `Lex`; unresolved variables yield `UnknownName`.

The VM charges one step per instruction and checks the operand-stack bound. `return 1;` needs two steps and one stack entry; `return 1+2;` needs four steps and two entries. Empty public IR blocks are rejected rather than traversed without consuming an instruction. Checked integer arithmetic returns `Overflow` for overflow **and division by zero**; the current API does not distinguish those cases.

[Binding regressions](tests/bindings.rs), [compile-budget regressions](tests/compile_budget.rs), [runtime/error boundaries](tests/limits.rs), and [preserved pipeline tests](tests/pipeline.rs) are executable specifications. The compile-budget regressions also failed before their implementation was added.

## Deliberate limits

Integer expressions and local bindings only. There is no type checker, serialized bytecode format, function system, I/O, network, optimizer, JIT, distributed execution or production sandbox. `Program` is public: runtime checks are not a complete verifier for arbitrary hand-authored IR. Allocation budgets are not wall-clock, operating-system memory, or process-isolation guarantees. These tests do not establish production use, performance superiority or sole human authorship.
