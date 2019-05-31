from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

import aiohttp
import ssl

# import json
import re


class ASSkill(Skill):
    async def _get_deployments(self):
        sites = self.config["sites"]
        return_text = f"*Account Services Deployments*\n"
        for site in sites:
            return_text = f"{return_text}```Deployment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    async def _get_accounts(self, deployment):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][deployment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/customers"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, ssl=sslcontext) as resp:
                data = await resp.json()
                return data["#collection"]

    async def _get_customer_id_by_name(self, deployment, name):
        account_list = await self._get_accounts(deployment)
        for account in account_list:
            search = re.search(re.escape(name), account["name"], re.IGNORECASE)
            if search:
                return account["id"]
        return None

    async def _get_account_by_name(self, deployment, name):
        customer_id = await self._get_customer_id_by_name(deployment, name)
        if customer_id:
            sslcontext = ssl.create_default_context(
                cafile=self.config["sites"][deployment]["ca"]
            )
            sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
            timeout = aiohttp.ClientTimeout(total=60)
            api_url = (
                f"{self.config['sites'][deployment]['url']}/customers/{customer_id}"
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, ssl=sslcontext) as resp:
                    data = await resp.json()
                    return data["#item"]
        else:
            return None

    async def _get_account_by_customer_id(self, deployment, customer_id):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][deployment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/customers/{customer_id}"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, ssl=sslcontext) as resp:
                data = await resp.json()
                if not resp.status == 200:
                    return None
                return data["#item"]

    async def _disable_account(self, deployment, customer_id):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][deployment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/customers/{customer_id}"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.delete(api_url, ssl=sslcontext) as resp:
                if resp.status == 204:
                    return "Account Disabled"
                elif resp.status == 404:
                    return "Account Not Found"
                else:
                    return "Something went wrong"

    async def _get_customer_id_by_account_id(self, deployment, account_id):
        account_list = await self._get_accounts(deployment)
        for account in account_list:
            for environment in account["environments"]:
                if account_id == environment["account_id"]:
                    return account["id"]
        return None

    async def _get_account_by_account_id(self, deployment, account_id):
        customer_id = await self._get_customer_id_by_account_id(deployment, account_id)
        if customer_id:
            sslcontext = ssl.create_default_context(
                cafile=self.config["sites"][deployment]["ca"]
            )
            sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
            timeout = aiohttp.ClientTimeout(total=60)
            api_url = (
                f"{self.config['sites'][deployment]['url']}/customers/{customer_id}"
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, ssl=sslcontext) as resp:
                    data = await resp.json()
                    return data["#item"]
        else:
            return None

    async def _add_account(self, deployment, name):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][deployment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/customers"
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {"#item": {"name": name, "products": []}}
            headers = {"content-type": "application/x.shr+json"}
            async with session.post(
                api_url, ssl=sslcontext, json=payload, headers=headers
            ) as resp:
                data = await resp.json()
                print(resp.status)
                print(data)
                return data["#item"]

    # Beging Matching functions

    @match_regex(r"^account services list deployments$")
    async def list_deployments(self, message):
        as_deployments = await self._get_deployments()

        await message.respond(f"{as_deployments}")

    @match_regex(r"^account services (?P<deployment>\w+-\w+|\w+) list accounts$")
    async def list_accounts(self, message):
        deployment = message.regex.group("deployment")
        accounts = await self._get_accounts(deployment)
        return_text = f"*{deployment} - Accounts*\n"
        for account in accounts:
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}\nStatus: {account['status']}```\n"
        await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) get account name: (?P<name>.*)$"
    )
    async def get_account_by_name(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        account = await self._get_account_by_name(deployment, name)
        return_text = f"*{deployment} - Account*\n"
        if account:
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}\nStatus: {account['status']}```\n"
            for environment in account["environments"]:
                return_text = f"{return_text}```Environment\n\tID: {environment['id']}\n\tType: {environment['env_type']}\n\tAccount ID: {environment['account_id']}\n\tSub Account ID: {environment['subaccount_id']}```\n"
            await message.respond(f"{return_text}")
        else:
            return_text = f"{return_text}```No Match```"
            await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) get account customer_id: (?P<customer_id>.*)$"
    )
    async def get_account_by_customer_id(self, message):
        deployment = message.regex.group("deployment")
        customer_id = message.regex.group("customer_id")
        account = await self._get_account_by_customer_id(deployment, customer_id)
        return_text = f"*{deployment} - Account*\n"
        if account:
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}\nStatus: {account['status']}```\n"
            for environment in account["environments"]:
                return_text = f"{return_text}```Environment\n\tID: {environment['id']}\n\tType: {environment['env_type']}\n\tAccount ID: {environment['account_id']}\n\tSub Account ID: {environment['subaccount_id']}```\n"
            await message.respond(f"{return_text}")
        else:
            return_text = f"{return_text}```No Match```"
            await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) get account account_id: (?P<account_id>.*)$"
    )
    async def get_account_by_account_id(self, message):
        deployment = message.regex.group("deployment")
        account_id = message.regex.group("account_id")
        account = await self._get_account_by_account_id(deployment, account_id)
        return_text = f"*{deployment} - Account*\n"
        if account:
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}\nStatus: {account['status']}```\n"
            for environment in account["environments"]:
                return_text = f"{return_text}```Environment\n\tID: {environment['id']}\n\tType: {environment['env_type']}\n\tAccount ID: {environment['account_id']}\n\tSub Account ID: {environment['subaccount_id']}```\n"
            await message.respond(f"{return_text}")
        else:
            return_text = f"{return_text}```No Match```"
            await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) add account name: (?P<name>.*)$"
    )
    async def add_account(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        check_account = await self._get_account_by_name(deployment, name)
        if not check_account:
            # Account Not Found
            account = await self._add_account(deployment, name)
            return_text = f"*{deployment} - Added Account*\n"
            return_text = f"{return_text}```Customer Name: {account['name']}\nCustomer ID: {account['id']}\nStatus: {account['status']}```\n"
            await message.respond(f"{return_text}")
        else:
            return_text = f"*{deployment} - Account Exists*\n"
            return_text = f"{return_text}```Customer Name: {check_account['name']}\nCustomer ID: {check_account['id']}\nStatus: {check_account['status']}```\n"
            await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) disable account customer_id: (?P<customer_id>.*)$"
    )
    async def disable_account(self, message):
        deployment = message.regex.group("deployment")
        customer_id = message.regex.group("customer_id")
        disabled = await self._disable_account(deployment, customer_id)
        return_text = f"*{deployment} - Disabled Account*\n"
        return_text = f"*{return_text}```{disabled}```"
        await message.respond(f"{disabled}")

