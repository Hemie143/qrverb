import qreader
from urllib.request import urlopen

'''
url = 'https://upload.wikimedia.org/wikipedia/commons/8/8f/Qr-2.png'
data = qreader.read(urlopen(url))
print(data)  # prints "Version 2"
'''

'''
url = 'https://img.geocaching.com/cache/large/fcc5a99c-6efb-4d68-bd5b-e4381641f952.gif'
data = qreader.read(urlopen(url))
print(data)  # prints "Version 2"

url = 'https://img.geocaching.com/cache/large/55a3b95b-fb55-4d21-acba-86004256e321.gif'
data = qreader.read(urlopen(url))
print(data)  # prints "Version 2"
'''

'''
import qrtools
from qrtools import qrtools
#qr = qrtools.qrtools.QR()
qr = qrtools.qrtools.QR()
qr.decode("qr_n.gif")
print(qr.data)
'''

# data = qreader.read('qr-2.png')
# data = qreader.read('qr_n.gif')
data = qreader.read('qr_e.gif')
print(data)

