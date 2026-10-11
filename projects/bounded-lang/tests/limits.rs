use bounded_lang::{Error, Limits, Op, Program, compile, run};
fn eval(source: &str) -> Result<i64, Error> {
    run(
        &compile(source)?,
        Limits {
            steps: 128,
            stack: 16,
        },
    )
}
#[test]
fn unknown_names_are_compile_errors() {
    assert_eq!(compile("return missing;"), Err(Error::UnknownName));
    assert_eq!(compile("let x = x + 1; return x;"), Err(Error::UnknownName));
}
#[test]
fn malformed_and_incomplete_sources_fail_without_panicking() {
    for input in [
        "",
        "return",
        "let x",
        "return (1",
        "let x = ; return x;",
        "return 1 @ 2;",
    ] {
        let result = std::panic::catch_unwind(|| compile(input));
        assert!(result.is_ok(), "panicked for {input:?}");
        assert!(result.unwrap().is_err(), "accepted {input:?}");
    }
}
#[test]
fn arithmetic_errors_are_explicit() {
    for input in [
        "return 9223372036854775807 + 1;",
        "return 3037000500 * 3037000500;",
        "return 1 / 0;",
        "return (0 - 9223372036854775807 - 1) / (0 - 1);",
        "return (0 - 9223372036854775807 - 1) - 1;",
    ] {
        assert_eq!(eval(input), Err(Error::Overflow), "{input}");
    }
    assert_eq!(eval("return 8 - 3 - 2;"), Ok(3));
    assert_eq!(eval("return 8 / 2 / 2;"), Ok(2));
}
#[test]
fn step_and_stack_limits_have_exact_boundaries() {
    let p = compile("return 1;").unwrap();
    assert_eq!(run(&p, Limits { steps: 2, stack: 1 }), Ok(1));
    assert_eq!(
        run(&p, Limits { steps: 1, stack: 1 }),
        Err(Error::StepLimit)
    );
    assert_eq!(
        run(&p, Limits { steps: 0, stack: 1 }),
        Err(Error::StepLimit)
    );
    assert_eq!(
        run(&p, Limits { steps: 2, stack: 0 }),
        Err(Error::StackLimit)
    );
    let p = compile("return 1 + 2;").unwrap();
    assert_eq!(run(&p, Limits { steps: 4, stack: 2 }), Ok(3));
    assert_eq!(
        run(&p, Limits { steps: 4, stack: 1 }),
        Err(Error::StackLimit)
    );
}
#[test]
fn malformed_ir_reports_errors() {
    for (ops, expected) in [
        (vec![Op::Load(0)], Error::UnknownName),
        (vec![Op::Ret], Error::StackUnderflow),
        (vec![Op::Add], Error::StackUnderflow),
        (vec![Op::Push(1)], Error::Parse),
    ] {
        assert_eq!(
            run(
                &Program {
                    ir: vec![ops],
                    locals: 0
                },
                Limits {
                    steps: 16,
                    stack: 8
                }
            ),
            Err(expected)
        );
    }
}
#[test]
fn local_count_cannot_wrap_after_65535_bindings() {
    let mut source = String::new();
    for n in 0..65536 {
        source.push_str(&format!("let n{n} = 1;"));
    }
    source.push_str("return n0;");
    assert_eq!(compile(&source).err(), Some(Error::Overflow));
}
