from io import BufferedIOBase

import six
import PIL.Image

from qreader.decoder import QRDecoder
from qreader.scanner import ImageScanner

__author__ = 'ewino'

__all__ = ['read']


def read(image_or_path):
    """
    Accepts either a path to a file, a PIL image, or a file-like object and reads a QR code data from it.
    :param str|PIL.Image.Image|file|BufferedIOBase image_or_path: The source containing the QR code.
    :return: The data encoded in the QR code.
    :rtype: str|unicode|int|qreader.vcard.vCard
    """
    if isinstance(image_or_path, (six.string_types + (BufferedIOBase,))) or \
            (six.PY2 and isinstance(image_or_path, file)):
        image_or_path = PIL.Image.open(image_or_path)
    if isinstance(image_or_path, PIL.Image.Image):
        qrscanner = ImageScanner(image_or_path)
        print('qrscanner: {}'.format(qrscanner.__dict__))
        print('Call QRDecoder')
        qrdecoder = QRDecoder(qrscanner)
        print('qrdecoder: {}'.format(qrdecoder.__dict__))
        print('Call QRDecoder.get_first')
        result = qrdecoder.get_first()
        return result
        # return QRDecoder(data).get_first()
        # result = QRDecoder(data).get_all()
        # if len(result) == 0:
        #     return None
        # elif len(result) == 1:
        #     return result[0]
        # else:
        #     return result
    raise TypeError('parameter should be a PIL image object, a file-like object, or a path to an image file')
