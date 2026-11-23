"""Encoding the @ipMatch operator's argument as a regular expression."""

from __future__ import annotations

import ipaddress

#regex for 1 octet of IPv4 address (number 0-255)
ANY_OCTET_REGEX = "(" + "[0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]" + ")"

#regex for 1 hexadec. digit of IPv6 address
ANY_HEX_DIGIT_REGEX = "[0-9a-fA-F]"

def octet_range_regex(lowest: int, highest: int) -> str:
    """Creates and returns a regex for number range lowest-highest, where the this range represents a range somewhere in 0-255."""

    #adding all the numbers in the range to the regex
    # TODO - optimization later (creates large regexes)
    regex = str(lowest)
    for num in range(lowest + 1, highest + 1):
        regex += "|" + str(num)
    
    return "(" + regex + ")"


def ipv4_or_ipv4_cidr_to_regex(entry: str) -> str:
    """Transforms the given IPv4 address or IPv4 CIDR block to a matching regular expression."""

    #creating a new network object and transforming its address to raw bytes
    net = ipaddress.IPv4Network(entry.strip(), strict=False)
    octets = net.network_address.packed

    parts = []
    for idx in range(4):
        #how many bits do not change in this octet (byte)
        fixed_bits_count = net.prefixlen - 8 * idx
        if fixed_bits_count > 8:
            fixed_bits_count = 8
        if fixed_bits_count < 0:
            fixed_bits_count = 0

        #all fixed -> appendins as they are; all variable -> appending the regex for the whole octet
        #otherwise -> creating the regex for the specific range
        curr_octet = octets[idx]
        if fixed_bits_count == 8:
            parts.append(str(curr_octet))
        elif fixed_bits_count == 0:
            parts.append(ANY_OCTET_REGEX)
        else:
            #computing the lowest and highest IPv4 addresses of the block
            free_bits = 8 - fixed_bits_count
            addr_count = 2 ** free_bits

            #alligning to the lowest address
            lowest_addr = (curr_octet // addr_count) * addr_count
            highest_addr = lowest_addr + addr_count - 1

            parts.append("(" + octet_range_regex(lowest_addr, highest_addr) + ")")
    return r"\.".join(parts)

def ipv6_shortened_variant(group_regexes: list[str], group_can_be_zero: list[bool]) -> list[str]:
    """Creates and returns regexes for all shortened variants of the passed IPv6 address using :: """

    variants = []
    for start in range(8):
        for end in range(start + 1, 9):
            #to be replaced by ::, all the digits must be able to be 0s
            if all(group_can_be_zero[start:end]):
                #all the remaining groups are kept the same
                variants.append((":".join(group_regexes[0:start])) 
                                + "::" 
                                + ":".join(group_regexes[end:]))

    return variants

def ipv6_or_ipv6_cidr_to_regex(entry: str) -> str:
    """Transforms the given IPv6 address or IPv6 CIDR block to a matching regular expression."""

    #the process is basically identical to the IPv4 processing
    net = ipaddress.IPv6Network(entry.strip(), strict=False)

    #the whole address as 32 individual, lowercase hexadec. digits
    hex_digits = net.network_address.packed.hex()

    digit_regexes = []
    #a helper array - true means the digit at the given position can be 0
    can_be_zero = []
    for idx in range(32):
        fixed_bits_count = net.prefixlen - 4 * idx
        if fixed_bits_count > 4:
            fixed_bits_count = 4
        if fixed_bits_count < 0:
            fixed_bits_count = 0

        curr_digit = int(hex_digits[idx], 16)
        if fixed_bits_count == 4:
            digit = hex_digits[idx]
            #making sure the regex is case-insensitive
            #e.g. 'c' -> '[cC]'
            if digit.isalpha():
                digit_regexes.append("[" + digit + digit.upper() + "]")
            else:
                digit_regexes.append(digit)
            can_be_zero.append(curr_digit == 0)
        elif fixed_bits_count == 0:
            digit_regexes.append(ANY_HEX_DIGIT_REGEX)
            can_be_zero.append(True)
        else:
            free_bits = 4 - fixed_bits_count
            value_count = 2 ** free_bits

            #aligning to the lowest value
            lowest_value = (curr_digit // value_count) * value_count
            highest_value = lowest_value + value_count - 1

            #listing the allowed characters for each digit
            allowed_digits = ""
            for value in range(lowest_value, highest_value + 1):
                allowed_digits += format(value, "x")

                #adding the Upper Case for the letters
                if value >= 10:
                    allowed_digits += format(value, "X")
            digit_regexes.append("[" + allowed_digits + "]")
            #if the lowesst possible value is not 0, the digit cannot possibly be zero
            can_be_zero.append(lowest_value == 0)

    #joining everything together - adding the ':' characters
    group_regexes = []
    group_can_be_zero = []
    for group_idx in range(8):
        #the current group
        start = 4 * group_idx
        end = start + 4
        group_digits = digit_regexes[start:end]
        digits_zero = can_be_zero[start:end]

        #all the possible variants of the same 4 hex. digits (all possible combinations of skipped leftmost 0s)
        possible_variants = []
        #1 to 3 0s can be skipped, e.g. :0020: -> :20:
        for idx in range(1, 5):
            skipped_zeros_count = 4 - idx
            if all(digits_zero[0:skipped_zeros_count]):
                #adding this particular variant - the currently skipped zeros are not added, while the rest of the group is added
                possible_variants.append("".join(group_digits[skipped_zeros_count:]))

        #e.g. :0020: -> (0020|020|20)
        group_regexes.append("(" + "|".join(possible_variants) + ")")
        #can all the digits of this group be zeros? -> if so, the whole group can be later skipped (::)
        group_can_be_zero.append(all(digits_zero))

    #assembling the full IPv6 address
    addresses = [":".join(group_regexes)]

    addresses.extend(ipv6_shortened_variant(group_regexes, group_can_be_zero))

    return "(" + "|".join(addresses) + ")"

def entry_to_regex(entry: str) -> str:
    net = ipaddress.ip_network(entry.strip(), strict=False)
    
    if net.version == 4:
        return ipv4_or_ipv4_cidr_to_regex(entry)
    elif net.version == 6:
        return ipv6_or_ipv6_cidr_to_regex(entry)
    else:
        raise ValueError(f"Invalid format of the @ipMatch argument: {entry}")
    
def ipmatch_to_regex(argument: str) -> str | None:
    """Parses a list of IPv4/IPv6 addresses or CIDR IPv4/IPv6 blocks separated by commas 
       and creates a regular expression out of them"""

    #e.g. "192.168.1.0/24, 10.1.0.1, 2001:0db0:0000:0000:0000:0000:0000:0000/32"
    entries = []
    parts = argument.split(",")

    for part in parts:
        if part.strip():
            entries.append(part.strip())

    #the string is empty, no regex returned
    if not entries:
        return None  

    return "^(" + "|".join(entry_to_regex(entry) for entry in entries) + ")$"