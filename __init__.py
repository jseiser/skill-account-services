from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

import aiohttp
import ssl

# import re


class ASSkill(Skill):
    async def _get_environments(self):
        sites = self.config["sites"]
        return_text = f"*Account Services Environments*\n"
        for site in sites:
            return_text = f"{return_text}```Environment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    async def _get_accounts(self, environment):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][environment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][environment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][environment]['url']}/customers"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, ssl=sslcontext) as resp:
                data = await resp.json()
                return data["#collection"]

    async def _get_account_id_by_name(self, environment, name):
        account_list = await self._get_accounts(environment)
        for account in account_list:
            if name.lower() == account["name"].lower():
                # search = re.search(re.escape(name), account["name"], re.IGNORECASE)
                # if search:
                return account["id"]
        return None

    async def _get_account_by_name(self, environment, name):
        customer_id = await self._get_account_id_by_name(environment, name)
        if customer_id:
            sslcontext = ssl.create_default_context(
                cafile=self.config["sites"][environment]["ca"]
            )
            sslcontext.load_cert_chain(self.config["sites"][environment]["cert"])
            timeout = aiohttp.ClientTimeout(total=60)
            api_url = (
                f"{self.config['sites'][environment]['url']}/customers/{customer_id}"
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, ssl=sslcontext) as resp:
                    data = await resp.json()
                    return data["#item"]
        else:
            return None

    async def _get_account_by_customer_id(self, environment, customer_id):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][environment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][environment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][environment]['url']}/customers/{customer_id}"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, ssl=sslcontext) as resp:
                data = await resp.json()
                if not resp.status == 200:
                    return None
                return data["#item"]

    # Beging Matching functions

    @match_regex(r"^account services list environments$")
    async def list_environments(self, message):
        as_environments = await self._get_environments()

        await message.respond(f"{as_environments}")

    @match_regex(r"^account services (?P<environment>\w+-\w+|\w+) list accounts$")
    async def list_accounts(self, message):
        environment = message.regex.group("environment")
        accounts = await self._get_accounts(environment)
        return_text = f"*{environment} - Accounts*\n"
        for account in accounts:
            return_text = f"{return_text}```Customer ID: {account['id']} Name: {account['name']} Status: {account['status']}```\n"
        await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<environment>\w+-\w+|\w+) get account name: (?P<name>.*)$"
    )
    async def get_account_by_name(self, message):
        environment = message.regex.group("environment")
        name = message.regex.group("name")
        account = await self._get_account_by_name(environment, name)
        return_text = f"*{environment} - Account*\n"
        if account:
            print(account)
            print(account["environments"])
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}```\n"
            for environment in account["environments"]:
                return_text = f"{return_text}```Environment\n\tID: {environment['id']}\n\tType: {environment['env_type']}\n\tAccount ID: {environment['account_id']}\n\tSub Account ID: {environment['subaccount_id']}```"
            await message.respond(f"{return_text}")
        else:
            return_text = f"{return_text}```No Match```"
            await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<environment>\w+-\w+|\w+) get account id: (?P<customer_id>.*)$"
    )
    async def get_account_by_customer_id(self, message):
        environment = message.regex.group("environment")
        customer_id = message.regex.group("customer_id")
        account = await self._get_account_by_customer_id(environment, customer_id)
        return_text = f"*{environment} - Account*\n"
        if account:
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}```\n"
            for environment in account["environments"]:
                return_text = f"{return_text}```Environment\n\tID: {environment['id']}\n\tType: {environment['env_type']}\n\tAccount ID: {environment['account_id']}\n\tSub Account ID: {environment['subaccount_id']}```"
            await message.respond(f"{return_text}")
        else:
            return_text = f"{return_text}```No Match```"
            await message.respond(f"{return_text}")
