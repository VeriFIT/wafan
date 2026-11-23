"""Encoding the @validateByteRange operator's argument as a SMT-LIB regular expression."""

from __future__ import annotations

from .transforms.url_decode import _smt_char_literal


def parse_and_get_byte_ranges(argument: str) -> list[tuple[int, int]]:
    """Parses the argument (e.g. "10, 12, 34-78") to a list of byte pairs.
       If an invalid argument/range is found, ValueError is raised.
       Single numbers are considered ranges with the same two boundaries."""

    ranges = []
    for part in argument.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            lowest_str, highest_str = part.split("-")
            lowest = int(lowest_str)
            highest = int(highest_str)
        else:
            lowest = int(part)
            highest = int(part)

        #valid numbers and valid range check
        if lowest < 0 or highest > 255 or highest < lowest:
            raise ValueError(f"'{part}' is not a valid byte range")
        
        ranges.append((lowest, highest))

    #the argument of @validateByteRange is mandatory
    if not ranges:
        raise ValueError("empty argument")
    
    return ranges


def allowed_bytes_to_SMTLIB_regex(argument: str, var_expr: str) -> str:
    """Creates a regex in SMT-lib format that matches the allowed bytes."""

    #for each allowed range, 1 re.range term is created (e.g. (re.range "\x20" "\x21")):
    range_terms = []
    for lowest, highest in parse_and_get_byte_ranges(argument):
        range_terms.append(
            f'(re.range "{_smt_char_literal(lowest)}" "{_smt_char_literal(highest)}")'
        )

    if len(range_terms) == 1:
        return f"(str.in_re {var_expr} (re.* {range_terms[0]}))"

    #more than 1 range -> 
    allowed_union =  "(re.union " + " ".join(range_terms) + ")"

    #the whole var_expr string must consist of the allowed bytes only
    return f"(str.in_re {var_expr} (re.* {allowed_union}))"

