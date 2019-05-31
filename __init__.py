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

    async def _disable_environment(self, deployment, customer_id, environment_id):
        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][deployment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/customers/{customer_id}/environments/{environment_id}"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.delete(api_url, ssl=sslcontext) as resp:
                if resp.status == 204:
                    return "Environment Disabled"
                elif resp.status == 404:
                    return "Environment Not Found"
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

    async def _verify_aid_type(self, deployment, account_id, account_type):
        account_exists = await self._get_account_by_account_id(deployment, account_id)
        if account_exists:
            return account_exists
        else:
            return None

    async def _get_subaccount_ids(self, deployment):
        accounts = await self._get_accounts(deployment)
        account_ids = list()
        for account in accounts:
            for environment in account["environments"]:
                account_ids.append(str(environment["account_id"]))
        return account_ids

    async def _add_environment(
        self, deployment, account_id, customer_id, account_type, subaccount_id=None
    ):
        if not account_type.upper() in ["DED", "FAWS", "FAZURE"]:
            return "Incorrect Account Type"

        if account_type.upper() == "DED":
            verify_aid_type = await self._verify_aid_type(
                deployment, account_id, account_type
            )
            if verify_aid_type:
                return "Core/DDI Exists"

        if subaccount_id:
            verify_subaccount_id = await self._get_subaccount_ids(deployment)

            if subaccount_id in verify_subaccount_id:
                return "Subsciption Exists"

        sslcontext = ssl.create_default_context(
            cafile=self.config["sites"][deployment]["ca"]
        )
        sslcontext.load_cert_chain(self.config["sites"][deployment]["cert"])
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/customers/{customer_id}/environments"
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {
                "#item": {
                    "account_id": account_id,
                    "subaccount_id": subaccount_id,
                    "env_type": account_type.upper(),
                    "auto_deploy": False,
                }
            }
            headers = {"content-type": "application/x.shr+json"}
            async with session.post(
                api_url, ssl=sslcontext, json=payload, headers=headers
            ) as resp:
                data = await resp.json()
                return data["#item"]

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

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) add environment customer_id: (?P<customer_id>.*) account_id: (?P<account_id>.*) type: (?P<type>FAWS|FAZURE|DED) subaccount_id: (?P<subaccount_id>.*)$"
    )
    async def add_environment_sub(self, message):
        deployment = message.regex.group("deployment")
        customer_id = message.regex.group("customer_id")
        account_id = message.regex.group("account_id")
        account_type = message.regex.group("type")
        subaccount_id = message.regex.group("subaccount_id")

        environment = await self._add_environment(
            deployment, account_id, customer_id, account_type, subaccount_id
        )

        return_text = f"*{deployment} - Add Environment*\n"
        add_errors = ["Incorrect Account Type", "Core/DDI Exists", "Subsciption Exists"]
        if environment in add_errors:
            return_text = f"{return_text}```{environment}```"
        else:
            return_text = f"{return_text}```Environment ID: {environment['id']}\nCustomer ID: {environment['customer_id']}\nAccount ID: {environment['id']}\nSub Account ID: {environment['subaccount_id']}\nType: {environment['env_type']}```\n"
        await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) add environment customer_id: (?P<customer_id>.*) account_id: (?P<account_id>.*) (?P<type>FAWS|FAZURE|DED)$"
    )
    async def add_environment(self, message):
        deployment = message.regex.group("deployment")
        customer_id = message.regex.group("customer_id")
        account_id = message.regex.group("account_id")
        account_type = message.regex.group("type")

        environment = await self._add_environment(
            deployment, account_id, customer_id, account_type
        )

        return_text = f"*{deployment} - Add Environment*\n"
        add_errors = ["Incorrect Account Type", "Core/DDI Exists", "Subsciption Exists"]
        print(environment)
        if environment in add_errors:
            return_text = f"{return_text}```{environment}```"
        else:
            return_text = f"{return_text}```Environment ID: {environment['id']}\nCustomer ID: {environment['customer_id']}\nAccount ID: {environment['id']}\nSub Account ID: {environment['subaccount_id']}\nType: {environment['env_type']}```\n"
        await message.respond(f"{return_text}")

    @match_regex(
        r"^account services (?P<deployment>\w+-\w+|\w+) disable environment customer_id: (?P<customer_id>.*) environment_id: (?P<environment_id>.*)$"
    )
    async def disable_environment(self, message):
        deployment = message.regex.group("deployment")
        customer_id = message.regex.group("customer_id")
        environment_id = message.regex.group("customer_id")
        disabled = await self._disable_environment(
            deployment, customer_id, environment_id
        )
        return_text = f"*{deployment} - DisabledEnvironmentt*\n"
        return_text = f"*{return_text}```{disabled}```"
        await message.respond(f"{disabled}")
