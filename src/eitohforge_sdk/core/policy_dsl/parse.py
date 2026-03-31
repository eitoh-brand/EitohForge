"""Lexer and parser for the policy expression DSL (no ``eval`` / code execution)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ast import And, Binary, Expr, Literal, Or, Ref, Unary


class PolicySyntaxError(SyntaxError):
    """Invalid policy expression source."""


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any = None
    pos: int = 0


_KEYWORDS = frozenset(
    {
        "and",
        "or",
        "not",
        "null",
        "true",
        "false",
        "in",
    }
)


def _lex(source: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    n = len(source)
    while i < n:
        c = source[i]
        if c.isspace():
            i += 1
            continue
        start = i
        if c == "(":
            tokens.append(_Token("LPAREN", pos=start))
            i += 1
            continue
        if c == ")":
            tokens.append(_Token("RPAREN", pos=start))
            i += 1
            continue
        if c == ".":
            tokens.append(_Token("DOT", pos=start))
            i += 1
            continue
        if c in "<>=!":
            if i + 1 < n:
                two = source[i : i + 2]
                if two in ("<=", ">=", "==", "!="):
                    tokens.append(_Token(two, pos=start))
                    i += 2
                    continue
            if c == "<":
                tokens.append(_Token("<", pos=start))
                i += 1
                continue
            if c == ">":
                tokens.append(_Token(">", pos=start))
                i += 1
                continue
            if c == "=":
                raise PolicySyntaxError(f"Unexpected '=' at position {start}; use '=='")
            if c == "!":
                raise PolicySyntaxError(f"Unexpected '!' at position {start}; use '!='")
        if c in "'\"":
            quote = c
            i += 1
            buf: list[str] = []
            while i < n:
                ch = source[i]
                if ch == "\\":
                    if i + 1 >= n:
                        raise PolicySyntaxError(f"Unterminated string escape at {start}")
                    nxt = source[i + 1]
                    if nxt in "\\\"'":
                        buf.append(nxt)
                    elif nxt == "n":
                        buf.append("\n")
                    else:
                        buf.append(nxt)
                    i += 2
                    continue
                if ch == quote:
                    i += 1
                    tokens.append(_Token("STRING", "".join(buf), pos=start))
                    break
                buf.append(ch)
                i += 1
            else:
                raise PolicySyntaxError(f"Unterminated string literal at {start}")
            continue
        if c.isdigit() or (c == "-" and i + 1 < n and source[i + 1].isdigit()):
            sign = 1
            if c == "-":
                sign = -1
                i += 1
            j = i
            seen_dot = False
            while j < n:
                ch = source[j]
                if ch.isdigit():
                    j += 1
                elif ch == "." and not seen_dot:
                    seen_dot = True
                    j += 1
                else:
                    break
            num_s = source[i:j]
            i = j
            if not num_s or num_s == ".":
                raise PolicySyntaxError(f"Invalid number at position {start}")
            if seen_dot:
                tokens.append(_Token("NUMBER", sign * float(num_s), pos=start))
            else:
                tokens.append(_Token("NUMBER", sign * int(num_s), pos=start))
            continue
        if c.isalpha() or c == "_":
            j = i + 1
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            i = j
            wl = word.lower()
            if wl in _KEYWORDS:
                tokens.append(_Token(wl.upper(), pos=start))
            else:
                tokens.append(_Token("IDENT", word, pos=start))
            continue
        raise PolicySyntaxError(f"Unexpected character {c!r} at position {start}")

    tokens.append(_Token("EOF", pos=n))
    return tokens


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._t = tokens
        self._i = 0

    def _peek(self) -> _Token:
        return self._t[self._i]

    def _advance(self) -> _Token:
        tok = self._peek()
        if tok.kind != "EOF":
            self._i += 1
        return tok

    def _expect(self, kind: str) -> _Token:
        tok = self._peek()
        if tok.kind != kind:
            raise PolicySyntaxError(f"Expected {kind!r} at position {tok.pos}, got {tok.kind!r}")
        return self._advance()

    def parse(self) -> Expr:
        expr = self._parse_or()
        if self._peek().kind != "EOF":
            raise PolicySyntaxError(f"Unexpected token at position {self._peek().pos}: {self._peek().kind!r}")
        return expr

    def _parse_or(self) -> Expr:
        left = self._parse_and()
        while self._peek().kind == "OR":
            self._advance()
            right = self._parse_and()
            left = Or(left, right)
        return left

    def _parse_and(self) -> Expr:
        left = self._parse_not()
        while self._peek().kind == "AND":
            self._advance()
            right = self._parse_not()
            left = And(left, right)
        return left

    def _parse_not(self) -> Expr:
        if self._peek().kind == "NOT":
            self._advance()
            return Unary("not", self._parse_not())
        return self._parse_comparison()

    def _parse_comparison(self) -> Expr:
        left = self._parse_primary()
        tok = self._peek()
        if tok.kind in ("==", "!=", "<", ">", "<=", ">="):
            op = self._advance().kind
            right = self._parse_primary()
            return Binary(left, op, right)
        if tok.kind == "NOT" and self._i + 1 < len(self._t) and self._t[self._i + 1].kind == "IN":
            self._advance()
            self._expect("IN")
            right = self._parse_primary()
            return Binary(left, "not_in", right)
        if tok.kind == "IN":
            self._advance()
            right = self._parse_primary()
            return Binary(left, "in", right)
        return left

    def _parse_primary(self) -> Expr:
        tok = self._peek()
        if tok.kind == "LPAREN":
            self._advance()
            inner = self._parse_or()
            self._expect("RPAREN")
            return inner
        if tok.kind == "NULL":
            self._advance()
            return Literal(None)
        if tok.kind == "TRUE":
            self._advance()
            return Literal(True)
        if tok.kind == "FALSE":
            self._advance()
            return Literal(False)
        if tok.kind == "STRING":
            self._advance()
            return Literal(tok.value)
        if tok.kind == "NUMBER":
            self._advance()
            return Literal(tok.value)
        if tok.kind == "IDENT":
            return self._parse_ref()
        raise PolicySyntaxError(f"Unexpected token at position {tok.pos}: {tok.kind!r}")

    def _parse_ref(self) -> Ref:
        parts: list[str] = []
        while True:
            tok = self._peek()
            if tok.kind != "IDENT":
                break
            self._advance()
            parts.append(str(tok.value))
            if self._peek().kind != "DOT":
                break
            self._advance()
            if self._peek().kind != "IDENT":
                raise PolicySyntaxError(f"Expected identifier after '.' at position {self._peek().pos}")
        if not parts:
            raise PolicySyntaxError("Expected identifier for reference")
        return Ref(tuple(parts))


def parse_expr(source: str) -> Expr:
    """Parse a policy expression string into an AST."""
    s = source.strip()
    if not s:
        raise PolicySyntaxError("Expression is empty.")
    tokens = _lex(s)
    return _Parser(tokens).parse()
