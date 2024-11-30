from contextlib import ExitStack

from discord import Locale
from discord.app_commands import (
    TranslationContextLocation,
    TranslationContextTypes,
    Translator,
    locale_str,
)
from fluent.runtime import FluentLocalization, FluentResourceLoader

from ghutils.resources import load_resource_dir
from ghutils.utils.l10n import command_description_id, parameter_description_id


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
        match string.extras:
            case {"id": str(msg_id)}:
                pass
            case _:
                match context.location:
                    case TranslationContextLocation.command_description:
                        msg_id = command_description_id(context.data.qualified_name)
                    case TranslationContextLocation.parameter_description:
                        msg_id = parameter_description_id(
                            command=context.data.command.qualified_name,
                            parameter=context.data.name,
                        )
                    case _:
                        msg_id = string.message

        result = self.l10n[locale].format_value(msg_id, string.extras)
        if result == msg_id:
            return string.message
        return result
