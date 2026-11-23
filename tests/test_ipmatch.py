"""Tests for the ipmatch.py module.

   Tests the correctness of the ipmatch_to_regex() function, which is essential for the @ipMatch operator support."""

import ipaddress
import random
import re

import pytest

from wafan.ipmatch import ipmatch_to_regex

def _matches(arg: str, ip: str) -> bool:
    """True, if the IP address matches the regex generated for it by the ipmatch_to_regex() function"""

    regex = ipmatch_to_regex(arg)
    return (regex is not None) and (re.fullmatch(regex, ip) is not None)

#---------------------General + Errors---------------------
def test_empty_is_none():
    assert ipmatch_to_regex("") is None
    assert ipmatch_to_regex(" , ") is None

@pytest.mark.parametrize("bad_input", [
    "adkj",
    "10.0.0.0/37",
    "10.2.0.256",
    "2001:db8:::1",
    "2001:db8::/129",
    "1:2:3:4:5:6:7:8:9",
])

def test_invalid_inputs_raise_value_error(bad_input):
    with pytest.raises(ValueError):
        ipmatch_to_regex(bad_input)

#---------------------IPv4---------------------
@pytest.mark.parametrize("net,ip,expected", [
    ("192.168.1.0/24", "192.168.1.50", True),
    ("192.168.1.0/24", "192.168.2.0", False),
    ("10.0.0.1", "10.0.0.1", True),
    ("10.0.0.1", "10.0.0.2", False),
])

def test_ipv4_networks(net, ip, expected):
    assert _matches(net, ip) == expected


def test_ipv4_leading_zeros_rejected():
    # Leading zeros in IPv4 octets should not match
    assert not _matches("10.0.0.1", "010.0.0.1")


#---------------------IPv6---------------------
@pytest.mark.parametrize("net,ip,expected", [
    #CIDR
    ("2001:db8::/32", "2001:db8:1::5", True),
    ("2001:db8::/32", "2001:db7::", False),

    #case-insensitivity (lower vs upper case)
    ("2001:db8::/32", "2001:DB8:1::5", True),
    ("2001:DB8::/32", "2001:0db8:0000:0000:0000:0000:0000:0001", True),

    #non-standard prefix
    ("2001:db8::/33", "2001:db8:7fff::", True),
    ("2001:db8::/33", "2001:db8:8000::", False),

    #shortened forms (::)
    ("::1", "::1", True),
    ("::1", "0:0:0:0:0:0:0:1", True),
    ("::1", "::2", False),
    ("fe80::/10", "FE80::1", True),
])

def test_ipv6_networks(net, ip, expected):
    assert _matches(net, ip) == expected

#---------------------Spaces in the argument---------------------
def test_comma_separated_list():
    arg = "192.168.1.1 , 2001:db8::/32, 10.0.0.0/8"
    assert _matches(arg, "192.168.1.1")
    assert _matches(arg, "2001:db8:abcd::1")
    assert _matches(arg, "10.5.5.5")
    assert not _matches(arg, "192.168.2.1")