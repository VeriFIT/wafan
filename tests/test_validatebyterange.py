"""Tests for the validatebyterange.py module.

   Tests the parse_and_get_byte_ranges() helper function and the generated SMT assert."""

import pytest

from wafan.validatebyterange import parse_and_get_byte_ranges
from wafan.smt import _op_validatebyterange

#---------------------Argument parsing---------------------
def test_parse():
    assert parse_and_get_byte_ranges("10, 13, 32-126") == [(10, 10), (13, 13), (32, 126)]

def test_parse_single_value():
    assert parse_and_get_byte_ranges("13") == [(13, 13)]

def test_parse_boundaries():
    assert parse_and_get_byte_ranges("0-255") == [(0, 255)]

@pytest.mark.parametrize("bad_input", ["", "abc", "5-1", "0-256", "-5", "1-", "1-2-3", "-4"])

def test_invalid_inputs_raise_value_error(bad_input):
    with pytest.raises(ValueError):
        parse_and_get_byte_ranges(bad_input)

#---------------------SMT assertion---------------------
def test_assert():
    #the operator  @validateByteRange matches if the value contains at least 1 B outside of the allowed ranges
    assert _op_validatebyterange("x", "1-255", False) == \
        '(not (str.in_re x (re.* (re.range "\\u{01}" "\\u{ff}"))))'

def test_negation():
    assert _op_validatebyterange("x", "13", True).startswith("(not (not")