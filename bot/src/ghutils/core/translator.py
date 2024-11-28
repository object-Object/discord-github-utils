from contextlib import ExitStack

from discord import Locale
from discord.app_commands import TranslationContextTypes, Translator, locale_str
from fluent.runtime import FluentLocalization, FluentResourceLoader

from ghutils.resources import load_resource_dir


class GHUtilsTranslator(Translator):
    async def load(self) -> None:
        self.exit_stack = ExitStack()

        path = self.exit_stack.enter_context(load_resource_dir("l10n"))
        loader = FluentResourceLoader(path.as_posix() + "/{locale}")

        self.l10n = {
            locale: FluentLocalization(
                locales=[locale.value, "en-US"],
                resource_ids=["main.ftl"],
                resource_loader=loader,
            )
            for locale in Locale
        }

    async def unload(self) -> None:
        self.exit_stack.close()

    async def translate(
        self,
        string: locale_str,
        locale: Locale,
        context: TranslationContextTypes,
    ) -> str | None:
        l10n = self.l10n[locale]
        return l10n.format_value(string.extras["id"])
