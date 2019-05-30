from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

import aiohttp
import ssl


class ASSkill(Skill):
    async def _get_environments(self):
        sites = self.config["sites"]
        return_text = f"*Account Services Environments*\n"
        for site in sites:
            return_text = f"{return_text}```Environment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    async def _get_customers(self, environment):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][environment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][environment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][environment]['url']}/customers"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, ssl=sslcontext) as resp:
                # return_text = f"*{environment} - Customers*\n"
                data = await resp.json()
                # for i in data["results"]:
                #     return_text = (
                #         f"{return_text}```ID: {i['id']} Name: {i['name']}```\n"
                #     )
                print(data["#collection"])
                return data

    # Beging Matching functions

    @match_regex(r"^account services list environments$")
    async def list_environments(self, message):
        as_environments = await self._get_environments()

        await message.respond(f"{as_environments}")

    @match_regex(r"^account services list customers (?P<environment>\w+-\w+|\w+)$")
    async def list_customers(self, message):
        environment = message.regex.group("environment")
        as_customers = await self._get_customers(environment)

        await message.respond(f"{as_customers}")
