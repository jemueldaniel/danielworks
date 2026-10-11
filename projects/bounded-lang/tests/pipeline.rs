use bounded_lang::{Limits, compile, run};
#[test]
fn end_to_end_lexer_parser_ir_vm() {
    let p = compile("let x = 2 + 3 * 4; return x - 5;").unwrap();
    assert_eq!(p.ir.len(), 2);
    assert_eq!(
        run(
            &p,
            Limits {
                steps: 64,
                stack: 16
            }
        )
        .unwrap(),
        9
    );
}
#[test]
fn malformed_input_is_rejected() {
    assert!(compile("let = 3; return 1;").is_err());
}
#[test]
fn execution_budget_is_enforced() {
    let p = compile("return 1+2+3+4;").unwrap();
    assert!(
        run(
            &p,
            Limits {
                steps: 2,
                stack: 16
            }
        )
        .is_err()
    );
}
#[test]
fn arithmetic_overflow_fails_closed() {
    let p = compile("return 9223372036854775807 + 1;").unwrap();
    assert!(
        run(
            &p,
            Limits {
                steps: 20,
                stack: 16
            }
        )
        .is_err()
    );
}
