from __future__ import absolute_import
from __future__ import unicode_literals

import io
import re

import pytest

from tokenize_rt import _re_partition
from tokenize_rt import ESCAPED_NL
from tokenize_rt import main
from tokenize_rt import Offset
from tokenize_rt import parse_string_literal
from tokenize_rt import reversed_enumerate
from tokenize_rt import rfind_string_parts
from tokenize_rt import src_to_tokens
from tokenize_rt import Token
from tokenize_rt import tokens_to_src
from tokenize_rt import UNIMPORTANT_WS


def test_re_partition_no_match():
    ret = _re_partition(re.compile('z'), 'abc')
    assert ret == ('abc', '', '')


def test_re_partition_match():
    ret = _re_partition(re.compile('b'), 'abc')
    assert ret == ('a', 'b', 'c')


def test_offset_default_values():
    assert Offset() == Offset(line=None, utf8_byte_offset=None)


def test_token_offset():
    token = Token('NAME', 'x', line=1, utf8_byte_offset=2)
    assert token.offset == Offset(line=1, utf8_byte_offset=2)


def test_src_to_tokens_simple():
    src = 'x = 5\n'
    ret = src_to_tokens(src)
    assert ret == [
        Token('NAME', 'x', line=1, utf8_byte_offset=0),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token('OP', '=', line=1, utf8_byte_offset=2),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token('NUMBER', '5', line=1, utf8_byte_offset=4),
        Token('NEWLINE', '\n', line=1, utf8_byte_offset=5),
        Token('ENDMARKER', '', line=2, utf8_byte_offset=0),
    ]


def test_src_to_tokens_escaped_nl():
    src = (
        'x = \\\n'
        '    5\n'
    )
    ret = src_to_tokens(src)
    assert ret == [
        Token('NAME', 'x', line=1, utf8_byte_offset=0),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token('OP', '=', line=1, utf8_byte_offset=2),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token(ESCAPED_NL, '\\\n', line=None, utf8_byte_offset=None),
        Token(UNIMPORTANT_WS, '    ', line=None, utf8_byte_offset=None),
        Token('NUMBER', '5', line=2, utf8_byte_offset=4),
        Token('NEWLINE', '\n', line=2, utf8_byte_offset=5),
        Token('ENDMARKER', '', line=3, utf8_byte_offset=0),
    ]


def test_src_to_tokens_escaped_nl_no_left_ws():
    src = (
        'x =\\\n'
        '    5\n'
    )
    ret = src_to_tokens(src)
    assert ret == [
        Token('NAME', 'x', line=1, utf8_byte_offset=0),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token('OP', '=', line=1, utf8_byte_offset=2),
        Token(ESCAPED_NL, '\\\n', line=None, utf8_byte_offset=None),
        Token(UNIMPORTANT_WS, '    ', line=None, utf8_byte_offset=None),
        Token('NUMBER', '5', line=2, utf8_byte_offset=4),
        Token('NEWLINE', '\n', line=2, utf8_byte_offset=5),
        Token('ENDMARKER', '', line=3, utf8_byte_offset=0),
    ]


def test_src_to_tokens_escaped_nl_windows():
    src = (
        'x = \\\r\n'
        '    5\r\n'
    )
    ret = src_to_tokens(src)
    assert ret == [
        Token('NAME', 'x', line=1, utf8_byte_offset=0),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token('OP', '=', line=1, utf8_byte_offset=2),
        Token(UNIMPORTANT_WS, ' ', line=None, utf8_byte_offset=None),
        Token(ESCAPED_NL, '\\\r\n', line=None, utf8_byte_offset=None),
        Token(UNIMPORTANT_WS, '    ', line=None, utf8_byte_offset=None),
        Token('NUMBER', '5', line=2, utf8_byte_offset=4),
        Token('NEWLINE', '\r\n', line=2, utf8_byte_offset=5),
        Token('ENDMARKER', '', line=3, utf8_byte_offset=0),
    ]


@pytest.mark.parametrize('prefix', ('f', 'ur', 'rb', 'F', 'UR', 'RB'))
def test_src_to_tokens_string_prefix_normalization(prefix):
    src = "{}'foo'\n".format(prefix)
    ret = src_to_tokens(src)
    assert ret == [
        Token('STRING', "{}'foo'".format(prefix), line=1, utf8_byte_offset=0),
        Token('NEWLINE', '\n', line=1, utf8_byte_offset=5 + len(prefix)),
        Token('ENDMARKER', '', line=2, utf8_byte_offset=0),
    ]


def test_src_to_tokens_octal_literal_normalization():
    ret = src_to_tokens('0755\n')
    assert ret == [
        Token('NUMBER', '0755', line=1, utf8_byte_offset=0),
        Token('NEWLINE', '\n', line=1, utf8_byte_offset=4),
        Token('ENDMARKER', '', line=2, utf8_byte_offset=0),
    ]


@pytest.mark.parametrize('postfix', ('l', 'L'))
def test_src_to_tokens_long_literal_normalization(postfix):
    src = '123{}\n'.format(postfix)
    ret = src_to_tokens(src)
    assert ret == [
        Token('NUMBER', '123{}'.format(postfix), line=1, utf8_byte_offset=0),
        Token('NEWLINE', '\n', line=1, utf8_byte_offset=4),
        Token('ENDMARKER', '', line=2, utf8_byte_offset=0),
    ]


@pytest.mark.parametrize(
    'filename',
    (
        'testing/resources/empty.py',
        'testing/resources/unicode_snowman.py',
        'testing/resources/backslash_continuation.py',
    ),
)
def test_roundtrip_tokenize(filename):
    with io.open(filename) as f:
        contents = f.read()
    ret = tokens_to_src(src_to_tokens(contents))
    assert ret == contents


def test_reversed_enumerate():
    tokens = src_to_tokens('x = 5\n')
    ret = reversed_enumerate(tokens)
    assert next(ret) == (6, Token('ENDMARKER', '', line=2, utf8_byte_offset=0))

    rest = list(ret)
    assert rest == [
        (5, Token(name='NEWLINE', src='\n', line=1, utf8_byte_offset=5)),
        (4, Token('NUMBER', '5', line=1, utf8_byte_offset=4)),
        (3, Token(UNIMPORTANT_WS, ' ')),
        (2, Token('OP', '=', line=1, utf8_byte_offset=2)),
        (1, Token(UNIMPORTANT_WS, ' ')),
        (0, Token('NAME', 'x', line=1, utf8_byte_offset=0)),
    ]


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('""', ('', '""')),
        ('u"foo"', ('u', '"foo"')),
        ('F"hi"', ('F', '"hi"')),
        ('r"""x"""', ('r', '"""x"""')),
    ),
)
def test_parse_string_literal(s, expected):
    assert parse_string_literal(s) == expected


@pytest.mark.parametrize('src', ('""', "b''", "f''", "r'''.'''"))
def test_rfind_string_parts_only_literal(src):
    tokens = src_to_tokens(src)
    assert rfind_string_parts(tokens, 0) == (0,)


@pytest.mark.parametrize(
    ('src', 'n', 'expected'),
    (
        ('"foo" "bar"', 2, (0, 2)),
        ('"""foo""" "bar"', 2, (0, 2)),
        (
            '(\n'
            '    "foo"\n'
            '    "bar"\n'
            ')',
            8,
            (3, 6),
        ),
        (
            'print(\n'
            '    "foo"\n'
            '    "bar"\n'
            ')',
            7,
            (4, 7),
        ),
    ),
)
def test_rfind_string_parts_multiple_tokens(src, n, expected):
    tokens = src_to_tokens(src)
    assert rfind_string_parts(tokens, n) == expected


def test_rfind_string_parts_not_a_string():
    tokens = src_to_tokens('print')
    assert rfind_string_parts(tokens, 0) == ()


@pytest.mark.parametrize(
    ('src', 'n'),
    (
        #           v
        ('x(1, "foo")', 6),
        #         v
        ('x ("foo")', 4),
        #           v
        ('x[0]("foo")', 6),
        #           v
        ('x(0)("foo")', 6),
    ),
)
def test_rfind_string_parts_end_of_call_looks_like_string(src, n):
    tokens = src_to_tokens(src)
    assert rfind_string_parts(tokens, n) == ()


@pytest.mark.parametrize(
    ('src', 'n', 'expected_i'),
    (
        #       v
        ('("foo")', 2, 1),
        #           v
        ('((("foo")))', 6, 3),
        #           v
        ('a + ("foo")', 6, 5),
        #            v
        ('a or ("foo")', 6, 5),
    ),
)
def test_rfind_string_parts_parenthesized(src, n, expected_i):
    tokens = src_to_tokens(src)
    assert rfind_string_parts(tokens, n) == (expected_i,)


def test_main(capsys):
    main(('testing/resources/simple.py',))
    out, _ = capsys.readouterr()
    assert out == (
        "1:0 NAME 'x'\n"
        "?:? UNIMPORTANT_WS ' '\n"
        "1:2 OP '='\n"
        "?:? UNIMPORTANT_WS ' '\n"
        "1:4 NUMBER '5'\n"
        "1:5 NEWLINE '\\n'\n"
        "2:0 ENDMARKER ''\n"
    )
