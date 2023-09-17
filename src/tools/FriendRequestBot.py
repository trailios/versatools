from Tool import Tool
import httpx
import concurrent.futures
from utils import Utils

class FriendRequestBot(Tool):
    def __init__(self, app):
        super().__init__("Friend Request Bot", "Send a lot of friend requests to a user", 5, app)

    def run(self):
        user_id = input("User ID to send friend requests to: ")

        cookies = self.get_cookies(self.config["max_generations"])

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        print("Please wait... \n")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config["max_workers"]) as self.executor:
            results = [self.executor.submit(self.send_friend_request, user_id, cookie) for cookie in cookies]

            for future in concurrent.futures.as_completed(results):
                try:
                    is_sent, response_text = future.result()
                except Exception as e:
                    is_sent, response_text = False, str(e)

                if is_sent:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_sent, "New requests")

    @Utils.retry_on_exception()
    def send_friend_request(self, user_id, cookie):
        """
        Send a friend request to a user
        """
        proxies = self.get_random_proxies() if self.config["use_proxy"] else None
        user_agent = self.get_random_user_agent()
        csrf_token = self.get_csrf_token(proxies, cookie)

        req_url = f"https://friends.roblox.com/v1/users/{user_id}/request-friendship"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = self.get_roblox_headers(user_agent, csrf_token)

        response = httpx.post(req_url, headers=req_headers, cookies=req_cookies, proxies=proxies)

        return (response.status_code == 200 and response.json()["success"]), response.text
