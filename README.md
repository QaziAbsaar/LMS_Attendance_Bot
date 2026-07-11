# LMS Attendance Bot

Auto login to PAF-IAST LMS, solve login CAPTCHA via HF OCR space, mark internship check-in/check-out with geofenced coordinates. Run manual or via cron.

## How it works

1. **Session init** — `requests.Session()` holds cookies across GET/POST.
2. **Token harvest** — parse login page HTML, grab `__RequestVerificationToken` (CSRF) and `CaptchaDeText` (CAPTCHA session hash).
3. **CAPTCHA extraction** — pull `<img id="CaptchaImage">` GIF stream, convert to RGB PNG via PIL.
4. **OCR** — send PNG to `toandev/OCR-for-Captcha` HF Space via `gradio_client`, strip non-alphanumeric noise from result.
5. **Login** — POST username, password, tokens, solved CAPTCHA. Success = redirect away from login URL.
6. **Attendance** — POST geofenced lat/lng/address to `/Internships/CheckIn` or `/CheckOut`.

## Setup

```bash
git clone <this-repo>
cd LMS_attendace
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`, fill real password:

```
LMS_USERNAME=your_reg_no
LMS_PASSWORD=your_password
INTERNSHIP_KEY=your_internship_key
LOCATION_LAT=33.607167
LOCATION_LNG=73.100716
LOCATION_ADDRESS=Nur Khan Base, NASTP Rd, Gharibabad, Chaklala Cantonment, Rawalpindi District, Rawalpindi Division, Punjab, 46330, Pakistan
```

`.env` is gitignored — never commit real credentials.

## Usage

```bash
python lms_attendance.py checkin
python lms_attendance.py checkout
```

## Deploy on Ubuntu (EC2 / cron)

```bash
sudo timedatectl set-timezone Asia/Karachi

sudo apt update
sudo apt install python3-pip python3-venv -y

mkdir -p ~/LMS_attendace
cd ~/LMS_attendace
# copy repo files here (git clone or scp)

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # fill real password + values
```

### Cron schedule (Mon–Fri, 9 AM check-in / 8 PM check-out)

```bash
crontab -e
```

Add:

```
0 9 * * 1-5 cd /home/ubuntu/LMS_attendace && /home/ubuntu/LMS_attendace/venv/bin/python lms_attendance.py checkin >> attendance.log 2>&1
0 20 * * 1-5 cd /home/ubuntu/LMS_attendace && /home/ubuntu/LMS_attendace/venv/bin/python lms_attendance.py checkout >> attendance.log 2>&1
```

### Logs

```bash
tail -f ~/LMS_attendace/attendance.log
```

## Notes

- CAPTCHA OCR depends on external HF Space uptime — failures logged, script exits clean, cron just retries next slot.
- `prod_captcha.png` temp file auto-deleted after each run.
- Geolocation values are spoofed client-side to match the required geofence — only works because LMS trusts client-submitted lat/lng.
