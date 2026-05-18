import pytest

from brief.spl.macro_expander import MacroExpander, MacroExpansionError


def test_no_macros_passthrough() -> None:
    spl = "index=main | stats count by host"
    assert MacroExpander.expand(spl, {}) == spl


def test_simple_no_arg_macro() -> None:
    macros = {"brief_default_index": {"definition": "index=main OR index=security"}}
    spl = "`brief_default_index` | stats count"
    expected = "index=main OR index=security | stats count"
    assert MacroExpander.expand(spl, macros) == expected


def test_macro_with_args_substitutes() -> None:
    macros = {
        "noise_filter(1)": {
            "args": "field",
            "definition": 'NOT $field$ IN ("system", "noreply")',
        }
    }
    spl = "index=main `noise_filter(user)` | stats count"
    expected = 'index=main NOT user IN ("system", "noreply") | stats count'
    assert MacroExpander.expand(spl, macros) == expected


def test_nested_macros_expand_to_fixed_point() -> None:
    macros = {
        "outer": {"definition": "`inner` | head 10"},
        "inner": {"definition": "index=main | search status=200"},
    }
    spl = "`outer`"
    expected = "index=main | search status=200 | head 10"
    assert MacroExpander.expand(spl, macros) == expected


def test_unknown_macro_left_intact() -> None:
    spl = "`mystery_macro` | stats count"
    assert MacroExpander.expand(spl, {}) == spl


def test_recursion_cap_blocks_self_reference() -> None:
    macros = {"loop": {"definition": "`loop` | stats count"}}
    with pytest.raises(MacroExpansionError):
        MacroExpander.expand("`loop`", macros)


def test_arity_disambiguation() -> None:
    macros = {
        "noise_filter": {"definition": "NOT noisy=1"},
        "noise_filter(1)": {
            "args": "field",
            "definition": "NOT $field$=noisy",
        },
    }
    assert "NOT noisy=1" in MacroExpander.expand("`noise_filter`", macros)
    assert "NOT user=noisy" in MacroExpander.expand("`noise_filter(user)`", macros)


def test_multi_arg_macro() -> None:
    macros = {
        "between(2)": {
            "args": "lo, hi",
            "definition": "count >= $lo$ AND count <= $hi$",
        }
    }
    spl = "... | where `between(5, 100)`"
    expected = "... | where count >= 5 AND count <= 100"
    assert MacroExpander.expand(spl, macros) == expected
