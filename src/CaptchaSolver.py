import base64
from anticaptchaofficial.funcaptchaproxyless import *
from anticaptchaofficial.funcaptchaproxyon import *
from twocaptcha import TwoCaptcha
import capsolver
from utils import Suppressor, Utils
import httpx
from urllib.parse import unquote

class CaptchaSolver:
    def __init__(self, captcha_service:str, api_key:str):
        self.captcha_service = captcha_service.lower()
        self.api_key = api_key

    @Utils.retry_on_exception()
    def get_rblx_public_key(self, user_agent:str, action_type:str, proxies:dict = None) -> str:
        """
        Gets the public key for the specified action type
        """
        reqpk_url = "https://apis.rbxcdn.com/captcha/v1/metadata"
        reqpk_headers = {"User-Agent": user_agent, "Accept": "*/*", "Accept-Language": "en-US;q=0.5,en;q=0.3", "Accept-Encoding": "gzip, deflate", "Origin": "https://www.roblox.com", "Referer": "https://www.roblox.com/", "Sec-Fetch-Dest": "empty",  "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "cross-site", "Te": "trailers", "Connection": "close", }
        reqpk_response = httpx.get(reqpk_url, headers=reqpk_headers, proxies=proxies)
        public_key = reqpk_response.json()["funCaptchaPublicKeys"][action_type]

        return public_key

    def solve_captcha(self, response:httpx.Response, action_type:str, user_agent:str, proxies:dict = None) -> httpx.Response:
        """
        Resolves a Roblox "Challenge is required..." request using the specified captcha service.
        Returns the captcha bypassed response from the request.
        """
        status_code = response.status_code
        response_headers = response.headers
        response_text = response.text

        if status_code == 423: # rate limited
            raise Exception(response_text)
        elif status_code != 403: # no captcha
            return response

        # get captcha data
        rblx_challenge_id = response_headers.get("Rblx-Challenge-Id")
        rblx_metadata = json.loads(base64.b64decode(response_headers.get("Rblx-Challenge-Metadata")))
        blob = rblx_metadata["dataExchangeBlob"]
        unified_captcha_id = rblx_metadata["unifiedCaptchaId"]
        public_key = self.get_rblx_public_key(user_agent, action_type, proxies)
        website_url = "https://www.roblox.com"
        website_subdomain = "roblox-api.arkoselabs.com"

        # solve captcha using specified service
        if self.captcha_service == "anti-captcha":
            solver = funcaptchaProxyless() # funcaptchaProxyon()
            solver.set_verbose(0)
            solver.set_key(self.api_key)
            solver.set_website_url(website_url)
            solver.set_website_key(public_key)

            # optional funcaptcha API subdomain, see our Funcaptcha documentation for details
            # solver.set_js_api_domain("client-api.arkoselabs.com")

            # optional data[blob] value, read the docs
            solver.set_data_blob('{"blob":"' + blob + '"}')

            # PROXY NOT SUPPORTED YET.
            #if use_proxy:
            #    solver.set_proxy_address(proxy_address)
            #    solver.set_proxy_port(proxy_port)
            #    solver.set_proxy_login(proxy_username)
            #    solver.set_proxy_password(proxy_password)
            #    if (user_agent != None):
            #        solver.set_user_agent(user_agent)

            # Specify softId to earn 10% commission with your app.
            # Get your softId here: https://anti-captcha.com/clients/tools/devcenter
            solver.set_soft_id(0)

            token = solver.solve_and_return_solution()

            if token == 0:
                raise Exception("task finished with error " + solver.error_code)
        elif self.captcha_service == "2captcha":
            solver = TwoCaptcha(self.api_key)

            result = solver.funcaptcha(
                sitekey=public_key,
                url=website_url,
                userAgent=user_agent,
                # PROXY NOT SUPPORTED YET.
                #proxy=({
                #    'type': proxy_type,
                #    'uri': f"{proxy_username+':'+proxy_password+'@' if use_proxy else ''}{proxy_address}:{proxy_port}"
                #} if use_proxy else None),
                **{"data[blob]": blob}
            )

            token = result["code"]
        elif self.captcha_service == "capsolver":
            capsolver.api_key = self.api_key
            with Suppressor():
                solution = capsolver.solve({
                    "type": "FunCaptchaTaskProxyLess",
                    "websitePublicKey": public_key,
                    "websiteURL": website_url,
                    "data": f"{{\"blob\":\"{blob}\"}}"
                })

            token = solution["token"]
        elif self.captcha_service == "capbypass":
            captcha_response = httpx.post('https://capbypass.com/api/createTask', json={
                "clientKey": self.api_key,
                "task": {
                    "type":"FunCaptchaTask",
                    "websiteURL": website_url,
                    "websitePublicKey": public_key,
                    "websiteSubdomain": website_subdomain,
                    "data[blob]": blob,
                    "proxy": ""
                }
            }, timeout=120)

            try:
                token = captcha_response.json()["solution"]["token"]
            except:
                if captcha_response.json().get("error") == "Key doesn't exist.":
                    raise Exception("Valid capbypass API key is required.")

                raise Exception(captcha_response.text)
        else:
            raise Exception("Captcha service not supported yet. Supported: anti-captcha, 2captcha, capsolver, capbypass")

        # build metadata containing token for login request
        metadata = f"{{\"unifiedCaptchaId\":\"{unified_captcha_id}\",\"captchaToken\":\"{token}\",\"actionType\":\"{rblx_metadata['actionType']}\"}}"
        metadata_base64 = base64.b64encode(metadata.encode()).decode()

        # send request again but with captcha token
        req_url = str(response.request.url)

        req_headers = json.loads((str(response.request.headers).replace("Headers(", "")[:-1]).replace("'", '"'))
        del req_headers["content-length"]
        req_headers['Rblx-Challenge-Id'] = rblx_challenge_id
        req_headers["Rblx-Challenge-Type"] = "captcha"
        req_headers["Rblx-Challenge-Metadata"] = metadata_base64

        # error bytes to json
        req_json = {}
        req_data = {}

        req_content = bytes.decode(response.request._content)

        if response.request.headers.get("content-type") == "application/x-www-form-urlencoded":
            pairs = req_content.split('&')
            for pair in pairs:
                key, value = pair.split('=')
                req_data[key] = unquote(value).replace('+', ' ')
        else:
            req_json = json.loads(req_content) if req_content != "" else {}

        req_json["captchaToken"] = token
        req_json["captchaId"] = unified_captcha_id
        req_json["captchaProvider"] = "PROVIDER_ARKOSE_LABS"

        final_response = httpx.post(req_url, headers=req_headers, json=req_json, data=req_data, proxies=proxies)

        return final_response

    def get_balance(self):
        """
        Gets the balance of the captcha service
        """
        if self.captcha_service == "anti-captcha":
            solver = funcaptchaProxyless() # or any other class
            solver.set_verbose(0)
            solver.set_key(self.api_key)
            balance = solver.get_balance()
        elif self.captcha_service == "2captcha":
            solver = TwoCaptcha(self.api_key)
            balance = solver.balance()
        elif self.captcha_service == "capsolver":
            capsolver.api_key = self.api_key

            with Suppressor():
                balance = capsolver.balance()["balance"]
        elif self.captcha_service == "capbypass":
            req_url = 'https://capbypass.com/api/getBalance'
            req_data = {
                'clientKey': self.api_key,
            }

            response = httpx.post(req_url, json=req_data)
            balance = response.json()["balance"]
            return balance
        else:
            raise Exception("Captcha service not found")

        return balance

    def __str__(self):
        return "A funcaptcha Solver using " + self.captcha_service + " as the captcha service."
