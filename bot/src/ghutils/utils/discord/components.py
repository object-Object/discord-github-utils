from typing import Any, Literal, overload

from discord import SelectOption
from discord.ui import ActionRow, Container, LayoutView, Select, View

type AnyComponentParent = View | LayoutView | ActionRow[Any] | Container[Any]


def update_select_menu_defaults(select: Select[Any]) -> list[SelectOption]:
    selected = set(select.values)
    result = list[SelectOption]()
    for option in select.options:
        option.default = option.value in selected
        if option.default:
            result.append(option)
    return result


@overload
def update_select_menu_default(
    select: Select[Any],
    required: Literal[True],
) -> SelectOption: ...


@overload
def update_select_menu_default(
    select: Select[Any],
    required: Literal[False] = False,
) -> SelectOption | None: ...


def update_select_menu_default(
    select: Select[Any],
    required: bool = False,
) -> SelectOption | None:
    selected = update_select_menu_defaults(select)
    if not required and not selected:
        return None
    return selected[0]
