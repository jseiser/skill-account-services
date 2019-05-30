from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

# import aiohttp


class ASSkill(Skill):
    async def _get_environments(self):
        sites = self.config["sites"]
        return_text = f"*Account Services Environments*\n"
        for site in sites:
            return_text = f"{return_text}```Environment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    @match_regex(r"^account services list environments$")
    async def list_environments(self, message):
        as_environments = await self._get_environments()

        await message.respond(f"{as_environments}")
