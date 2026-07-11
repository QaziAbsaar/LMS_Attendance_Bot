import requests
from gradio_client import Client, handle_file
from bs4 import BeautifulSoup
from PIL import Image
import argparse
from datetime import datetime
import urllib.parse
import io
import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────
LOGIN_URL = "https://lms.paf-iast.edu.pk/StudentAccount/Account/Login?ReturnUrl=%2F"
BASE_URL = "https://lms.paf-iast.edu.pk"
ATTENDANCE_URL = f"{BASE_URL}/Internships"
HF_SPACE = "toandev/OCR-for-Captcha"

USERNAME = os.environ["LMS_USERNAME"]
PASSWORD = os.environ["LMS_PASSWORD"]
INTERNSHIP_KEY = os.environ["INTERNSHIP_KEY"]

LAT = os.environ["LOCATION_LAT"]
LNG = os.environ["LOCATION_LNG"]
LOC_ADDRESS = os.environ["LOCATION_ADDRESS"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Linux",
    "Origin": BASE_URL,
    "Referer": LOGIN_URL
}


def solve_captcha(image_path):
    print(f"[*] Submitting CAPTCHA to {HF_SPACE}...")
    try:
        client = Client(HF_SPACE)
        result = client.predict(
            handle_file(image_path),
            api_name="/predict"
        )
        return ''.join(e for e in result if e.isalnum()).upper()
    except Exception as e:
        print(f"[-] Hugging Face API exception: {e}")
        return None


def execute_workflow(action):
    print(f"[*] Starting {action.upper()} routine at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. Load login page, grab session cookies
    print("[*] Contacting portal for session state...")
    res = session.get(LOGIN_URL)
    soup = BeautifulSoup(res.text, 'html.parser')

    verification_token = ""
    token_element = soup.find('input', {'name': '__RequestVerificationToken'})
    if token_element:
        verification_token = token_element.get('value', '')
        print("[+] Extracted __RequestVerificationToken")

    captcha_de_text = ""
    captcha_de_element = soup.find('input', {'name': 'CaptchaDeText'})
    if captcha_de_element:
        captcha_de_text = captcha_de_element.get('value', '')
        print("[+] Extracted CaptchaDeText")

    # 2. Locate captcha image
    captcha_img_element = soup.find('img', id='CaptchaImage')
    if not captcha_img_element:
        print("[-] Error: could not find CAPTCHA image element on login page.")
        return

    captcha_src = captcha_img_element.get('src')
    captcha_url = urllib.parse.urljoin(BASE_URL, captcha_src)
    print(f"[+] CAPTCHA endpoint: {captcha_url}")

    # 3. Download and normalize captcha image
    print("[*] Downloading CAPTCHA image...")
    captcha_res = session.get(captcha_url)

    img = Image.open(io.BytesIO(captcha_res.content))
    img = img.convert("RGB")
    captcha_path = "prod_captcha.png"
    img.save(captcha_path, "PNG")

    # 4. OCR via Hugging Face space
    captcha_text = solve_captcha(captcha_path)
    if os.path.exists(captcha_path):
        os.remove(captcha_path)

    if not captcha_text:
        print("[-] CAPTCHA solving failed. Aborting.")
        return
    print(f"[+] CAPTCHA text: {captcha_text}")

    # 5. Login
    print("[*] Submitting login form...")
    login_payload = {
        "RegNo": USERNAME,
        "Password": PASSWORD,
        "CaptchaInputText": captcha_text,
        "CaptchaDeText": captcha_de_text,
        "__RequestVerificationToken": verification_token
    }

    login_res = session.post(LOGIN_URL, data=login_payload)

    if "login" in login_res.url.lower():
        print("[-] Login rejected. Check credentials or CAPTCHA accuracy.")
        return
    print("[+] Login confirmed.")

    # 6. Post attendance
    print(f"[*] Dispatching {action.upper()} request...")
    endpoint = f"{ATTENDANCE_URL}/CheckIn" if action == "checkin" else f"{ATTENDANCE_URL}/CheckOut"

    payload = {
        f"Check{'In' if action == 'checkin' else 'Out'}Lat": LAT,
        f"Check{'In' if action == 'checkin' else 'Out'}Lng": LNG,
        f"Check{'In' if action == 'checkin' else 'Out'}Location": LOC_ADDRESS,
        "key": INTERNSHIP_KEY
    }

    try:
        response = session.post(endpoint, data=payload)
        print(f"[+] Response status: {response.status_code}")
        print(f"[*] Response snippet: {response.text[:300].strip()}")
    except Exception as e:
        print(f"[!] Attendance request failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LMS internship attendance automation")
    parser.add_argument("action", choices=["checkin", "checkout"], help="Attendance action to perform")
    args = parser.parse_args()

    execute_workflow(args.action)
