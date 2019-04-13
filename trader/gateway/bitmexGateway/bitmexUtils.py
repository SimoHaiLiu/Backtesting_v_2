# encoding: UTF-8
import base64
import hashlib
import hmac
import json
import re
import urllib
from urllib import quote
import zlib
import gzip
from copy import copy
from datetime import datetime
import time

#----------------------------------------------------------------------
def _split_url(url):
    """
    将url拆分为host和path
    :return: host, path
    """
    m = re.match('\w+://([^/]*)(.*)', url)
    if m:
        return m.group(1), m.group(2)


#----------------------------------------------------------------------
def createSignature(apiKey, method, host, path, secretKey, getParams=None):
    """
    创建签名
    :param getParams: dict 使用GET方法时附带的额外参数(urlparams)
    :return:
    """
    expires = int(time.time()+5)
    method = "GET"
    path = "/realtime"
    msg = method + path + str(expires)
    signature = hmac.new(
        secretKey, msg.encode(), digestmod=hashlib.sha256
    ).hexdigest()
    
    return [apiKey, expires, signature]

#----------------------------------------------------------------------
def createSignatureRest(secKey, request):
    """
    Generate BitMEX signature.
    """
    
    # BITMEX http only accepts "" not '', so workround is to replace url encoded str from 27 to 22!!!
    # Sign
    expires = int(time.time() + 5)

    if request.params:
        query = urllib.urlencode(request.params)
        path = request.path + "?" + query
    else:
        path = request.path

    if request.data:
        if 'orders' not in request.data:
            request.data = urllib.urlencode(request.data)
        else:
            request.data = urllib.urlencode(request.data).replace('27','22')
    else:
        request.data = ""

    msg = request.method + "/api/v1" + path + str(expires) + request.data
    signature = hmac.new(
        secKey, msg.encode(), digestmod=hashlib.sha256
    ).hexdigest()
    
    return expires, signature