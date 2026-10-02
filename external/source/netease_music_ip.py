import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import requests
import json

SOURCE_NAME = "netease_music_ip"

def a(length):
    """Generate a random string of specified length"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    result = ""
    for _ in range(length):
        e = random.randint(0, len(chars) - 1)
        result += chars[e]
    return result

def b(text, key):
    """AES encrypt with CBC mode"""
    # Convert key and IV to bytes
    key_bytes = key.encode('utf-8')
    iv_bytes = "0102030405060708".encode('utf-8')
    text_bytes = text.encode('utf-8')
    
    # Pad the text to be a multiple of 16 bytes (AES block size)
    padded_text = pad(text_bytes, AES.block_size)
    
    # Create AES cipher in CBC mode
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    
    # Encrypt and return base64 encoded string
    encrypted = cipher.encrypt(padded_text)

    return base64.b64encode(encrypted).decode('utf-8')

def c(text, public_exponent, modulus):
    """RSA encrypt using manual implementation"""
    # Convert hex strings to integers
    exp = int(public_exponent, 16)
    mod = int(modulus, 16)
    
    # Convert text to integer (reverse the string as per original JS implementation)
    text_reversed = text[::-1]
    text_bytes = text_reversed.encode('utf-8')
    text_int = int.from_bytes(text_bytes, byteorder='big')
    
    # Perform RSA encryption: ciphertext = (plaintext ^ exponent) mod modulus
    encrypted_int = pow(text_int, exp, mod)
    
    # Convert to hex string
    encrypted_hex = hex(encrypted_int)[2:]  # Remove '0x' prefix
    
    return encrypted_hex

def d(text, public_exponent, modulus, initial_key):
    """Main encryption function"""
    result = {}
    random_key = a(16)
    
    # First AES encryption with initial_key
    enc_text = b(text, initial_key)
    
    # Second AES encryption with random_key
    result['params'] = b(enc_text, random_key)
    
    # RSA encrypt the random_key
    result['encSecKey'] = c(random_key, public_exponent, modulus)
    
    return result

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
}

def get_source(source):
    uid = source["uid"]
    text = '{"userId":"'+uid+'"}'
    pub_exp = "010001"
    modulus = "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
    initial_key = "0CoJUm6Qyw8W8jud"
    
    encrypted_data = d(text, pub_exp, modulus, initial_key)
    
    netease_record_req = requests.post("https://interface.music.163.com/weapi/user/tag/list?csrf_token=", data=encrypted_data, headers=headers, timeout=10)
    netease_record_raw_data = netease_record_req.json()
    return json.dumps(netease_record_raw_data["data"]["tags"][0])