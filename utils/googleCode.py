# !/usr/bin/python
# -*- coding:utf-8 -*-
import pyotp
import os
from qrcode import QRCode, constants


def get_qrcode(secret_key, username):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    filepath = BASE_DIR + '/'
    data = pyotp.totp.TOTP(secret_key).provisioning_uri(username, issuer_name="Verfiy Code")
    qr = QRCode(
        version=1,
        error_correction=constants.ERROR_CORRECT_L,
        box_size=6,
        border=4,
    )
    try:
        print(data)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image()
        img.save(filepath+secret_key+'.png')    # 保存条形码图片
        return True
    except Exception as e:
        print(e)
        return False


def Google_Verify_Result(secret_key, verifycode):
    t = pyotp.TOTP(secret_key)
    result = t.verify(verifycode) # 对输入验证码进行校验，正确返回True
    msg = result if result is True else False
    return msg


if __name__ == '__main__':
    #gtoken = pyotp.random_base32()
    #print(gtoken)
    #print(get_qrcode(gtoken, 'pengzuyun@gmail.com'))
    #from config import USERS_AUTH
    # print(Google_Verify_Result(USERS_AUTH['pengzuyun@gmail.com'], '022489'))
    print(Google_Verify_Result('XIIXWIZ3XXWJC36G', '027966'))