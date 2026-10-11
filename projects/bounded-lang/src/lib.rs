#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    Lex,
    Parse,
    UnknownName,
    Overflow,
    StepLimit,
    StackLimit,
    StackUnderflow,
    CompileLimit,
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Tok {
    Let,
    Return,
    Id(String),
    Int(i64),
    Plus,
    Minus,
    Star,
    Slash,
    Eq,
    Semi,
    LParen,
    RParen,
    Eof,
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Expr {
    Int(i64),
    Name(String),
    Bin(char, Box<Expr>, Box<Expr>),
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Stmt {
    Let(String, Expr),
    Return(Expr),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Op {
    Push(i64),
    Load(u16),
    Store(u16),
    Add,
    Sub,
    Mul,
    Div,
    Ret,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Program {
    pub ir: Vec<Vec<Op>>,
    pub locals: u16,
}
#[derive(Debug, Clone, Copy)]
pub struct Limits {
    pub steps: u64,
    pub stack: usize,
}
fn lex(s: &str) -> Result<Vec<Tok>, Error> {
    let mut o = vec![];
    let mut it = s.chars().peekable();
    while let Some(&c) = it.peek() {
        if c.is_whitespace() {
            it.next();
            continue;
        }
        if c.is_ascii_digit() {
            let mut n = String::new();
            while it.peek().is_some_and(|x| x.is_ascii_digit()) {
                n.push(it.next().unwrap())
            }
            o.push(Tok::Int(n.parse().map_err(|_| Error::Lex)?));
            continue;
        }
        if c.is_ascii_alphabetic() || c == '_' {
            let mut n = String::new();
            while it
                .peek()
                .is_some_and(|x| x.is_ascii_alphanumeric() || *x == '_')
            {
                n.push(it.next().unwrap())
            }
            o.push(match n.as_str() {
                "let" => Tok::Let,
                "return" => Tok::Return,
                _ => Tok::Id(n),
            });
            continue;
        }
        it.next();
        o.push(match c {
            '+' => Tok::Plus,
            '-' => Tok::Minus,
            '*' => Tok::Star,
            '/' => Tok::Slash,
            '=' => Tok::Eq,
            ';' => Tok::Semi,
            '(' => Tok::LParen,
            ')' => Tok::RParen,
            _ => return Err(Error::Lex),
        })
    }
    o.push(Tok::Eof);
    Ok(o)
}
struct Parser {
    t: Vec<Tok>,
    i: usize,
}
impl Parser {
    fn cur(&self) -> &Tok {
        &self.t[self.i]
    }
    fn take(&mut self) -> Tok {
        let x = self.t[self.i].clone();
        self.i += 1;
        x
    }
    fn expr(&mut self, min: u8) -> Result<Expr, Error> {
        let mut l = match self.take() {
            Tok::Int(n) => Expr::Int(n),
            Tok::Id(n) => Expr::Name(n),
            Tok::LParen => {
                let e = self.expr(0)?;
                if self.take() != Tok::RParen {
                    return Err(Error::Parse);
                }
                e
            }
            _ => return Err(Error::Parse),
        };
        loop {
            let (op, p) = match self.cur() {
                Tok::Plus => ('+', 1),
                Tok::Minus => ('-', 1),
                Tok::Star => ('*', 2),
                Tok::Slash => ('/', 2),
                _ => break,
            };
            if p < min {
                break;
            }
            self.take();
            let r = self.expr(p + 1)?;
            l = Expr::Bin(op, Box::new(l), Box::new(r))
        }
        Ok(l)
    }
    fn program(&mut self) -> Result<Vec<Stmt>, Error> {
        let mut out = vec![];
        while *self.cur() != Tok::Eof {
            match self.take() {
                Tok::Let => {
                    let Tok::Id(n) = self.take() else {
                        return Err(Error::Parse);
                    };
                    if self.take() != Tok::Eq {
                        return Err(Error::Parse);
                    };
                    let e = self.expr(0)?;
                    if self.take() != Tok::Semi {
                        return Err(Error::Parse);
                    };
                    out.push(Stmt::Let(n, e))
                }
                Tok::Return => {
                    let e = self.expr(0)?;
                    if self.take() != Tok::Semi {
                        return Err(Error::Parse);
                    };
                    out.push(Stmt::Return(e))
                }
                _ => return Err(Error::Parse),
            }
        }
        if !matches!(out.last(), Some(Stmt::Return(_))) {
            return Err(Error::Parse);
        }
        Ok(out)
    }
}
fn emit(
    e: &Expr,
    names: &std::collections::BTreeMap<String, u16>,
    o: &mut Vec<Op>,
) -> Result<(), Error> {
    match e {
        Expr::Int(n) => o.push(Op::Push(*n)),
        Expr::Name(n) => o.push(Op::Load(*names.get(n).ok_or(Error::UnknownName)?)),
        Expr::Bin(c, a, b) => {
            emit(a, names, o)?;
            emit(b, names, o)?;
            o.push(match c {
                '+' => Op::Add,
                '-' => Op::Sub,
                '*' => Op::Mul,
                '/' => Op::Div,
                _ => return Err(Error::Parse),
            })
        }
    }
    Ok(())
}
/// Hard source and per-statement limits bound lexing and recursive AST work.
pub const MAX_SOURCE_BYTES: usize = 1_048_576;
pub const MAX_STATEMENT_TOKENS: usize = 256;

pub fn compile(source: &str) -> Result<Program, Error> {
    if source.len() > MAX_SOURCE_BYTES {
        return Err(Error::CompileLimit);
    }
    let toks = lex(source)?;
    let mut statement_tokens = 0usize;
    for token in &toks {
        if matches!(token, Tok::Semi | Tok::Eof) {
            statement_tokens = 0;
        } else {
            statement_tokens += 1;
            if statement_tokens > MAX_STATEMENT_TOKENS {
                return Err(Error::CompileLimit);
            }
        }
    }
    let ast = Parser { t: toks, i: 0 }.program()?;
    let mut names = std::collections::BTreeMap::new();
    // Binding count is separate from the number of currently visible names.
    let mut locals = 0u16;
    let mut ir = vec![];
    for s in ast {
        let mut code = vec![];
        match s {
            Stmt::Let(n, e) => {
                emit(&e, &names, &mut code)?;
                // Resolve the initializer first, so shadowing can use its previous value.
                let slot = locals;
                locals = locals.checked_add(1).ok_or(Error::Overflow)?;
                names.insert(n, slot);
                code.push(Op::Store(slot))
            }
            Stmt::Return(e) => {
                emit(&e, &names, &mut code)?;
                code.push(Op::Ret)
            }
        }
        ir.push(code)
    }
    Ok(Program { ir, locals })
}
pub fn run(p: &Program, l: Limits) -> Result<i64, Error> {
    let mut locals = vec![0i64; p.locals as usize];
    let mut st = Vec::new();
    let mut steps = 0u64;
    for block in &p.ir {
        // Compiler-produced blocks always contain instructions. Reject malformed
        // empty blocks so visiting public IR cannot bypass the instruction budget.
        if block.is_empty() {
            return Err(Error::Parse);
        }
        for op in block {
            steps = steps.checked_add(1).ok_or(Error::StepLimit)?;
            if steps > l.steps {
                return Err(Error::StepLimit);
            };
            match *op {
                Op::Push(n) => st.push(n),
                Op::Load(i) => st.push(*locals.get(i as usize).ok_or(Error::UnknownName)?),
                Op::Store(i) => {
                    let v = st.pop().ok_or(Error::StackUnderflow)?;
                    *locals.get_mut(i as usize).ok_or(Error::UnknownName)? = v
                }
                Op::Add | Op::Sub | Op::Mul | Op::Div => {
                    let b = st.pop().ok_or(Error::StackUnderflow)?;
                    let a = st.pop().ok_or(Error::StackUnderflow)?;
                    let v = match op {
                        Op::Add => a.checked_add(b),
                        Op::Sub => a.checked_sub(b),
                        Op::Mul => a.checked_mul(b),
                        Op::Div => a.checked_div(b),
                        _ => None,
                    }
                    .ok_or(Error::Overflow)?;
                    st.push(v)
                }
                Op::Ret => return st.pop().ok_or(Error::StackUnderflow),
            }
            if st.len() > l.stack {
                return Err(Error::StackLimit);
            }
        }
    }
    Err(Error::Parse)
}
#[cfg(test)]
mod unit {
    use super::*;
    #[test]
    fn precedence() {
        assert_eq!(
            run(
                &compile("return 2+3*4;").unwrap(),
                Limits {
                    steps: 20,
                    stack: 8
                }
            )
            .unwrap(),
            14
        )
    }
    #[test]
    fn unknown_name() {
        assert_eq!(compile("return x;"), Err(Error::UnknownName));
    }
}
