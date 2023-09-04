import os
import concurrent.futures
import requests
from Tool import Tool
from utils import Utils

class CookieChecker(Tool):
    def __init__(self, app):
        super().__init__("Cookie Checker", "Checks if cookies are valid and shuffle and unduplicate them.", 1, app)

        self.delete_invalid_cookies = self.config["delete_invalid_cookies"]
        self.use_proxy = self.config["use_proxy"]
        self.max_workers = self.config["max_workers"]

        self.cache_file_path = os.path.join(self.cache_directory, "verified-cookies.txt")
    
    def run(self):
        cookies = self.get_cookies()

        f = open(self.cache_file_path, 'w')
        f.seek(0)
        f.truncate()

        working_cookies = 0
        failed_cookies = 0
        total_cookies = len(cookies)

        print("Please wait... \n ")

        # for each line, test the proxy
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = [executor.submit(self.test_cookie, cookie, self.use_proxy) for cookie in cookies]

            for future in concurrent.futures.as_completed(results):
                try:
                    is_working, cookie, response_text = future.result()
                    working_cookies += 1
                except Exception as e:
                    is_working, response_text = False, str(e)
                    failed_cookies += 1

                if not (self.delete_invalid_cookies and not is_working):
                    f.write(cookie + "\n") 

                self.print_status(working_cookies, failed_cookies, total_cookies, response_text, is_working, "Working")

        f.close()
        os.replace(self.cache_file_path, self.cookies_file_path)

    @Utils.retry_on_exception
    def test_cookie(self, cookie, use_proxy):
        user_agent = self.get_random_user_agent()
        proxies = self.get_random_proxies() if use_proxy else None

        req_url = "https://www.roblox.com/mobileapi/userinfo"
        req_cookies = { ".ROBLOSECURITY": cookie }
        req_headers = {"User-Agent": user_agent, "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US;q=0.5,en;q=0.3", "Accept-Encoding": "gzip, deflate", "Content-Type": "application/json;charset=utf-8", "Origin": "https://www.roblox.com", "Referer": "https://www.roblox.com/", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site", "Te": "trailers"}

        response = requests.get(req_url, headers=req_headers, cookies=req_cookies, proxies=proxies)

        result = response.json()

        user_id = result["UserID"]
        username = result["UserName"]
        robux_balance = result["RobuxBalance"]

        return True, cookie, f"UserID: {user_id} | Username: {username} | Robux Balance: {robux_balance}"