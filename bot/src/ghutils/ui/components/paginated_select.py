from __future__ import annotations

import logging
from typing import Any, Callable, Literal, Self, override

from discord import Interaction, SelectOption
from discord.abc import MISSING
from discord.ui import ActionRow, LayoutView, Select, View
from discord.ui.item import ContainedItemCallbackType
from discord.ui.select import SelectCallbackDecorator

from ghutils.utils.types import AsyncCallable

logger = logging.getLogger(__name__)

# randomly generated UUIDs
PREVIOUS_PAGE_VALUE = "e4215656-23ba-4a3d-8386-795778944b4b"
NEXT_PAGE_VALUE = "1e1f5d4c-e908-42cf-8d6c-8b66aadf0998"

MAX_PAGE_LENGTH = 23


type PageGetter[V: View | LayoutView] = AsyncCallable[
    [V, Interaction, PaginatedSelect[V], int],
    list[SelectOption],
]


class PaginatedSelect[V: View | LayoutView](Select[V]):
    _inner_callback: ContainedItemCallbackType[V | ActionRow[Any], Self] | None
    _page_getter: PageGetter[V] | None
    _page_cache: dict[int, list[SelectOption]]

    _page: int
    _selected_page: int | None
    _selected_index: int | None

    def __init__(
        self,
        *,
        custom_id: str = MISSING,
        placeholder: None = None,
        min_values: Literal[0, 1] = 1,
        max_values: Literal[0, 1] = 1,
        options: list[SelectOption] = MISSING,
        disabled: bool = False,
        required: bool = True,
        row: int | None = None,
        id: int | None = None,
        inner_callback: ContainedItemCallbackType[V | ActionRow[Any], Self]
        | None = None,
        page_getter: PageGetter[V] | None = None,
    ) -> None:
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
            required=required,
            row=row,
            id=id,
        )

        # TODO: implement?
        if self.max_values > 1:
            raise NotImplementedError("PaginatedSelect does not support multi-select")

        self._inner_callback = inner_callback
        self._page_getter = page_getter
        self._page_cache = {}
        self._page = 1
        self._selected_page = None
        self._selected_index = None

        if options is not MISSING:
            # reuse the logic in the decorator
            self.options = options

    async def fetch_first_page(self, interaction: Interaction):
        """Fetch and switch to page 1."""
        self._page_cache.pop(1, None)
        await self._switch_to_page(interaction, 1)

    def clear_cached_pages(self):
        self._page_cache.clear()

    @property
    def page_getter(self):
        """A decorator to set the page getter function.

        The page getter receives a 1-indexed page number to fetch, and should return up
        to 23 select options. If a page has less than 23 options, it is assumed to be
        the final page.
        """
        return self._decorate_page_getter

    @page_getter.setter
    def page_getter(self, page_getter: PageGetter[V] | None):
        self._page_getter = page_getter

    def _decorate_page_getter(self) -> Callable[[PageGetter[V]], PageGetter[V]]:
        def decorator(page_getter: PageGetter[V]) -> PageGetter[V]:
            self._page_getter = page_getter
            return page_getter

        return decorator

    @property
    @override
    def options(self) -> list[SelectOption]:
        # https://stackoverflow.com/a/59313599
        assert Select.options.fget is not None
        return Select.options.fget(self)

    @options.setter
    @override
    def options(self, value: list[SelectOption]):
        if len(value) > MAX_PAGE_LENGTH:
            raise ValueError(
                f"Pages must not contain more than {MAX_PAGE_LENGTH} options (got {len(value)})"
            )

        assert Select.options.fset is not None
        Select.options.fset(self, value)

        self._page_cache[self._page] = self.options.copy()

        for i, option in enumerate(self.options):
            if option.default:
                self._selected_page = self._page
                self._selected_index = i
                break

        # sanity check: don't add page selection options if they're already added
        # (this hopefully shouldn't happen)
        if self.options and (
            self.options[0].value == PREVIOUS_PAGE_VALUE
            or self.options[-1].value == NEXT_PAGE_VALUE
            or len(self.options) > MAX_PAGE_LENGTH
        ):
            return

        # NOTE: we need to check this *before* mutating self.options
        if (
            # only allow going to the next page if the current page is full
            len(self.options) == MAX_PAGE_LENGTH
            # and either the next page has values or we haven't fetched it yet
            and self._page_cache.get(self._page + 1, True)
        ):
            self.options.append(
                SelectOption(
                    emoji="➡️",
                    label=f"Page {self._page + 1}",
                    value=NEXT_PAGE_VALUE,
                )
            )

        if self._page > 1:
            self.options.insert(
                0,
                SelectOption(
                    emoji="⬅️",
                    label=f"Page {self._page - 1}",
                    value=PREVIOUS_PAGE_VALUE,
                ),
            )

    @property
    def selected_option(self) -> SelectOption | None:
        if self._selected_page is None or self._selected_index is None:
            return None

        if self._selected_page == self._page:
            index = self._selected_index
            if self._page > 1:
                # skip the back option
                index += 1
            return self.options[index]

        return self._page_cache[self._selected_page][self._selected_index]

    @selected_option.setter
    def selected_option(self, option: None):
        self._selected_page = None
        self._selected_index = None

    @override
    async def callback(self, interaction: Interaction):
        """The callback associated with this UI item.

        This can be overridden by subclasses, but subclasses should prefer to override
        `inner_callback` in most cases.
        """
        if selected := set(self.values):
            if PREVIOUS_PAGE_VALUE in selected:
                # go to previous page
                await self._switch_to_page(interaction, self._page - 1)
                if interaction.response.is_done():
                    await interaction.edit_original_response(view=self.view)
                else:
                    await interaction.response.edit_message(view=self.view)

            elif NEXT_PAGE_VALUE in selected:
                # go to next page
                await self._switch_to_page(interaction, self._page + 1)
                if interaction.response.is_done():
                    await interaction.edit_original_response(view=self.view)
                else:
                    await interaction.response.edit_message(view=self.view)

            else:
                # normal selection
                if self.selected_option:
                    self.selected_option.default = False

                self._selected_page = self._page

                for i, option in enumerate(self.options):
                    if option.value in selected:
                        self._selected_index = i - 1 if self._page > 1 else i
                        option.default = True
                        break

                self._clear_remote_page_selection()

                await self.inner_callback(interaction)

        else:
            # deselected
            if self.selected_option:
                self.selected_option.default = False
                self.selected_option = None
                self._clear_remote_page_selection()

            await self.inner_callback(interaction)

    async def inner_callback(self, interaction: Interaction):
        """The callback associated with this UI item. Not called when switching pages.

        This can be overridden by subclasses. The default implementation calls the
        function decorated by `paginated_select`, if any.
        """
        if self._inner_callback:
            assert self.view is not None
            await self._inner_callback(self.view, interaction, self)

    async def _switch_to_page(self, interaction: Interaction, page: int):
        if page < 1:
            page = 1

        if (options := self._page_cache.get(page)) is None:
            assert self._page_getter
            assert self.view
            options = await self._page_getter(self.view, interaction, self, page)
            if len(options) > MAX_PAGE_LENGTH:
                raise ValueError(
                    f"Pages must not contain more than {MAX_PAGE_LENGTH} options (got {len(options)})"
                )
            self._page_cache[page] = options

        # if an option on the current page is selected, mark it as default
        # we use a loop to ensure *only* the selected option is marked
        for i, option in enumerate(options):
            option.default = self._selected_page == page and self._selected_index == i

        # note: the options setter checks option.default
        self._page = page
        self.options = options

        # if an option on a different page is selected, set the placeholder
        # and update the description of the option pointing at that page
        if self.selected_option and self._selected_page != page:
            self.placeholder = self.selected_option.label

            assert self._selected_page is not None
            self.options[
                0 if self._selected_page < page else -1
            ].description = f"(selected on page {self._selected_page})"
        else:
            self.placeholder = None

    def _clear_remote_page_selection(self):
        self.placeholder = None

        if self.options[0].value == PREVIOUS_PAGE_VALUE:
            self.options[0].description = None

        if self.options[-1].value == NEXT_PAGE_VALUE:
            self.options[-1].description = None


def paginated_select[
    S: View | LayoutView | ActionRow[Any],
    SelectT: PaginatedSelect[Any],
](
    *,
    options: list[SelectOption] = MISSING,
    custom_id: str = MISSING,
    min_values: Literal[0, 1] = 1,
    max_values: Literal[0, 1] = 1,
    disabled: bool = False,
    row: int | None = None,
    id: int | None = None,
) -> SelectCallbackDecorator[S, SelectT]:
    def decorator(inner_callback: ContainedItemCallbackType[Any, Any]) -> SelectT:
        select = PaginatedSelect[Any](
            options=options,
            custom_id=custom_id,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
            row=row,
            id=id,
            inner_callback=inner_callback,
        )
        return select  # pyright: ignore[reportReturnType]

    return decorator
