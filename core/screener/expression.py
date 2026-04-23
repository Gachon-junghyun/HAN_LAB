# FILE: core/screener/expression.py
#
# 수식 파서 & 평가 엔진
#
# 수식 예시:
#   rsi(_, 14) < 30 && cci(_, 20) > 100        ← 스크리닝 모드 (_=전체 종목)
#   close("005930") > sma("005930", 60)         ← 단일 종목 평가
#   obv(_, 17, 1) > 0 && obv(_, 17) < 0        ← shift: 마지막 인자가 N이면 N일 전

import operator
import pickle
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yfinance as yf

from .indicators import INDICATOR_REGISTRY, compute_indicator

# ── OHLCV 로더 ─────────────────────────────────────────────────────────────
# OHLCVDownloader 로 사전 다운로드했다면 pkl 캐시를 먼저 사용.
# 없으면 yfinance 직접 다운로드 (느림).
_DEFAULT_CACHE_DIR = Path("ohlcv_cache")


def _load_ohlcv(code: str, cache_dir: Path = _DEFAULT_CACHE_DIR) -> pd.DataFrame:
    pkl_path = cache_dir / f"{code}.pkl"
    if pkl_path.exists():
        df = pickle.load(open(pkl_path, "rb"))
    else:
        df = yf.download(f"{code}.KS", period="1y", progress=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df


# 평가 세션 중 같은 종목 반복 다운로드 방지용 인메모리 캐시
_session_cache: dict[str, pd.DataFrame] = {}
_cache_dir: Path = _DEFAULT_CACHE_DIR


def set_cache_dir(path: str | Path) -> None:
    """OHLCVDownloader 와 같은 cache_dir 로 맞출 때 사용"""
    global _cache_dir
    _cache_dir = Path(path)


def _get_ohlcv(code: str) -> pd.DataFrame:
    if code not in _session_cache:
        _session_cache[code] = _load_ohlcv(code, _cache_dir)
    return _session_cache[code]


def clear_cache() -> None:
    _session_cache.clear()


# ── 토크나이저 ─────────────────────────────────────────────────────────────
_TOKEN_PATTERNS = [
    ("NUMBER",      r"-?\d+\.?\d*"),
    ("STRING",      r'"[^"]*"'),
    ("IDENT",       r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("LPAREN",      r"\("),
    ("RPAREN",      r"\)"),
    ("COMMA",       r","),
    ("AND",         r"&&"),
    ("OR",          r"\|\|"),
    ("NOT",         r"!(?!=)"),
    ("GTE",         r">="),
    ("LTE",         r"<="),
    ("GT",          r">"),
    ("LT",          r"<"),
    ("EQ",          r"=="),
    ("NEQ",         r"!="),
    ("PLACEHOLDER", r"_"),
    ("WS",          r"\s+"),
]
_TOKEN_RE = re.compile("|".join(f"(?P<{n}>{p})" for n, p in _TOKEN_PATTERNS))


class Token:
    __slots__ = ("type", "value")

    def __init__(self, type_: str, value: str):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


def tokenize(expr: str) -> list[Token]:
    return [
        Token(m.lastgroup, m.group())
        for m in _TOKEN_RE.finditer(expr)
        if m.lastgroup != "WS"
    ]


# ── AST 노드 ───────────────────────────────────────────────────────────────
class ASTNode:
    pass


class Literal(ASTNode):
    def __init__(self, value):
        self.value = value


class FuncCall(ASTNode):
    def __init__(self, name: str, args: list):
        self.name = name
        self.args = args


class BinOp(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right


class UnaryOp(ASTNode):
    def __init__(self, op: str, operand: ASTNode):
        self.op = op
        self.operand = operand


class Compare(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right


# ── 파서 ───────────────────────────────────────────────────────────────────
class ParseError(Exception):
    pass


class Parser:
    """
    Grammar:
        expr      → or_expr
        or_expr   → and_expr (|| and_expr)*
        and_expr  → not_expr (&& not_expr)*
        not_expr  → ! not_expr | cmp_expr
        cmp_expr  → value (CMP_OP value)?
        value     → func_call | NUMBER | ( expr )
        func_call → IDENT ( args )
        args      → ( arg (, arg)* )?
        arg       → STRING | NUMBER | PLACEHOLDER
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected: Optional[str] = None) -> Token:
        tok = self.peek()
        if tok is None:
            raise ParseError(f"Unexpected end (expected {expected})")
        if expected and tok.type != expected:
            raise ParseError(f"Expected {expected}, got {tok.type} ({tok.value!r})")
        self.pos += 1
        return tok

    def parse(self) -> ASTNode:
        node = self._or()
        if self.pos < len(self.tokens):
            raise ParseError(f"Unexpected token: {self.tokens[self.pos]}")
        return node

    def _or(self) -> ASTNode:
        left = self._and()
        while self.peek() and self.peek().type == "OR":
            self.consume("OR")
            left = BinOp("or", left, self._and())
        return left

    def _and(self) -> ASTNode:
        left = self._not()
        while self.peek() and self.peek().type == "AND":
            self.consume("AND")
            left = BinOp("and", left, self._not())
        return left

    def _not(self) -> ASTNode:
        if self.peek() and self.peek().type == "NOT":
            self.consume("NOT")
            return UnaryOp("not", self._not())
        return self._cmp()

    def _cmp(self) -> ASTNode:
        left = self._value()
        _CMP = {"GT", "LT", "GTE", "LTE", "EQ", "NEQ"}
        if self.peek() and self.peek().type in _CMP:
            op = self.consume()
            return Compare(op.type, left, self._value())
        return left

    def _value(self) -> ASTNode:
        tok = self.peek()
        if tok is None:
            raise ParseError("Unexpected end of expression")
        if tok.type == "LPAREN":
            self.consume("LPAREN")
            node = self._or()
            self.consume("RPAREN")
            return node
        if tok.type == "NUMBER":
            self.consume()
            return Literal(float(tok.value))
        if tok.type == "IDENT":
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == "LPAREN":
                return self._func_call()
            self.consume()
            return Literal(float(tok.value) if tok.value.replace(".", "").lstrip("-").isdigit() else tok.value)
        raise ParseError(f"Unexpected token: {tok}")

    def _func_call(self) -> ASTNode:
        name = self.consume("IDENT").value
        self.consume("LPAREN")
        args = []
        if self.peek() and self.peek().type != "RPAREN":
            args.append(self._arg())
            while self.peek() and self.peek().type == "COMMA":
                self.consume("COMMA")
                args.append(self._arg())
        self.consume("RPAREN")
        return FuncCall(name, args)

    def _arg(self) -> Any:
        tok = self.peek()
        if tok.type == "STRING":
            self.consume()
            return tok.value.strip('"')
        if tok.type == "NUMBER":
            self.consume()
            v = float(tok.value)
            return int(v) if v == int(v) else v
        if tok.type in ("PLACEHOLDER", "IDENT") and tok.value == "_":
            self.consume()
            return "_"
        raise ParseError(f"Invalid argument: {tok}")


# ── 평가기 ─────────────────────────────────────────────────────────────────
_CMP_OPS = {
    "GT": operator.gt, "LT": operator.lt,
    "GTE": operator.ge, "LTE": operator.le,
    "EQ": operator.eq, "NEQ": operator.ne,
}


def evaluate(node: ASTNode, target_code: Optional[str] = None) -> Any:
    """
    AST 평가. target_code: 스크리닝 모드에서 '_' 자리 종목코드.
    """
    if isinstance(node, Literal):
        return node.value

    if isinstance(node, FuncCall):
        name = node.name
        if name not in INDICATOR_REGISTRY:
            raise ValueError(f"Unknown indicator: {name}")
        args = list(node.args)
        if not args:
            raise ValueError(f"{name}() requires a stock code as first argument")

        code = args[0]
        if code == "_":
            if target_code is None:
                raise ValueError("Placeholder '_' used without target_code")
            code = target_code

        _, defaults = INDICATOR_REGISTRY[name]
        params = dict(defaults)
        param_names = list(defaults.keys())
        rest = args[1:]
        shift = 0
        if len(rest) > len(param_names):
            shift = int(rest[-1])
            rest = rest[:-1]
        for i, v in enumerate(rest):
            if i < len(param_names):
                params[param_names[i]] = v

        df = _get_ohlcv(code)
        if df.empty:
            return 0.0
        return compute_indicator(name, df, shift=shift, **params)

    if isinstance(node, Compare):
        return _CMP_OPS[node.op](evaluate(node.left, target_code), evaluate(node.right, target_code))

    if isinstance(node, BinOp):
        if node.op == "and":
            return evaluate(node.left, target_code) and evaluate(node.right, target_code)
        return evaluate(node.left, target_code) or evaluate(node.right, target_code)

    if isinstance(node, UnaryOp):
        return not evaluate(node.operand, target_code)

    raise ValueError(f"Cannot evaluate: {node}")


# ── 공개 API ───────────────────────────────────────────────────────────────
def parse_expression(expr: str) -> ASTNode:
    """수식 문자열 → AST"""
    return Parser(tokenize(expr)).parse()


def eval_expression(expr: str, target_code: Optional[str] = None) -> Any:
    """
    수식 평가.

    예) eval_expression('rsi("005930", 14)')          → 65.3
        eval_expression('cci(_, 20) > 100', "005930") → True/False
    """
    return evaluate(parse_expression(expr), target_code)


def eval_expression_safe(
    expr: str, target_code: Optional[str] = None
) -> tuple[bool, Any, Optional[str]]:
    """에러 시 크래시 없이 (success, result, error_msg) 반환"""
    try:
        return (True, eval_expression(expr, target_code), None)
    except Exception as e:
        return (False, None, str(e))
