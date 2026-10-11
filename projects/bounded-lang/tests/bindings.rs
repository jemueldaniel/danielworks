use bounded_lang::{Limits, compile, run};

#[test]
fn repeated_binding_shadows_without_invalid_local_slot() {
    let p = compile("let x = 1; let x = 2; return x;").unwrap();
    assert_eq!(
        run(
            &p,
            Limits {
                steps: 32,
                stack: 8
            }
        ),
        Ok(2)
    );
    assert_eq!(p.locals, 2);
}

#[test]
fn shadow_initializer_uses_previous_binding_and_later_names_do_not_alias() {
    let p = compile("let x = 1; let x = x + 1; let y = 7; return x + y;").unwrap();
    assert_eq!(
        run(
            &p,
            Limits {
                steps: 64,
                stack: 8
            }
        ),
        Ok(9)
    );
    assert_eq!(p.locals, 3);
}
