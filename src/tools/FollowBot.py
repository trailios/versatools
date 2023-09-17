import httpx
from Tool import Tool
import concurrent.futures
from CaptchaSolver import CaptchaSolver

class FollowBot(Tool):
    def __init__(self, app):
        super().__init__("Follow Bot", "Increase Followers count of a user", 4, app)

    def run(self):
        user_id = input("User ID to increase followers count: ")

        cookies = self.get_cookies(self.config["max_generations"])

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        print("Please wait... \n")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config["max_workers"]) as self.executor:
            results = [self.executor.submit(self.send_follow_request, self.config["captcha_solver"], user_id, cookie) for cookie in cookies]

            for future in concurrent.futures.as_completed(results):
                try:
                    is_followed, response_text = future.result()
                except Exception as e:
                    is_followed, response_text = False, str(e)

                if is_followed:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, is_followed, "New followers")

    def send_follow_request(self, captcha_service:str, user_id:str | int, cookie:str):
        """
        Send a follow request to a user
        """
        captcha_solver = CaptchaSolver(captcha_service, self.captcha_tokens[captcha_service])
        proxies = self.get_random_proxies() if self.config["use_proxy"] else None
        user_agent = self.get_random_user_agent()
        csrf_token = self.get_csrf_token(proxies, cookie)

        req_url = f"https://friends.roblox.com/v1/users/{user_id}/follow"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = self.get_roblox_headers(user_agent, csrf_token)

        init_res = httpx.post(req_url, headers=req_headers, cookies=req_cookies, proxies=proxies)
        response = captcha_solver.solve_captcha(init_res, "ACTION_TYPE_FOLLOW_USER", user_agent, proxies)

        return (response.status_code == 200), response.text
