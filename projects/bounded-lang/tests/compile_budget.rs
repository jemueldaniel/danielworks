use bounded_lang::{Error, Limits, Op, Program, compile, run};

#[test]
fn source_size_is_bounded_before_lexing() {
    let mut text = String::from("return 1;");
    text.push_str(&" ".repeat(1_048_576 - text.len()));
    assert!(compile(&text).is_ok());
    text.push(' ');
    assert!(compile(&text).is_err(), "oversized source must be rejected");
}

#[test]
fn nested_expression_has_a_compile_budget() {
    let allowed = format!("return {}1{};", "(".repeat(127), ")".repeat(127));
    assert!(compile(&allowed).is_ok());
    let rejected = format!("return {}1{};", "(".repeat(128), ")".repeat(128));
    assert!(
        compile(&rejected).is_err(),
        "nested expressions must be bounded"
    );
}

#[test]
fn flat_expression_has_a_compile_budget() {
    let allowed = format!("return {};", vec!["1"; 128].join("+"));
    assert_eq!(
        run(
            &compile(&allowed).unwrap(),
            Limits {
                steps: 256,
                stack: 2
            }
        ),
        Ok(128)
    );
    let rejected = format!("return {};", vec!["1"; 129].join("+"));
    assert!(
        compile(&rejected).is_err(),
        "flat AST emission must also be bounded"
    );
}

#[test]
fn empty_public_ir_blocks_are_rejected_not_traversed_for_free() {
    let p = Program {
        ir: vec![vec![], vec![Op::Push(1), Op::Ret]],
        locals: 0,
    };
    assert_eq!(run(&p, Limits { steps: 2, stack: 1 }), Err(Error::Parse));
}
