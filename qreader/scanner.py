from collections import Iterator

from qreader import tuples
from qreader.exceptions import QrImageRecognitionException
from qreader.spec import get_mask_func, FORMAT_INFO_MASK, get_dead_zones, ec_level_from_format_info_code
from qreader.validation import validate_format_info, validate_data

__author__ = 'ewino'

WHITE = 0
BLACK = 1

# TODO: merge both classes
# TODO: rename Scanner.read and _was_read

class Scanner(object):
    def __init__(self):
        self._was_read = False

    def read_info(self):
        raise NotImplementedError()

    def _read_all_data(self):
        raise NotImplementedError()

    # Iteration methods #

    def reset(self):
        print('***************************************************************Scanner.reset: {}'.format(self._was_read))
        self._current_index = -1



class ImageScanner(Scanner):
    def __init__(self, image):
        """
        :type image: PIL.Image.Image
        :return:
        """
        print('ImageScanner.__init__')
        super(ImageScanner, self).__init__()
        self._current_index = -1
        self._data_len = 0
        self._info = None
        self.data = None
        self.image = image.convert('LA')  # gray-scale it baby!
        self.mask = None
        self.parseImage()

    def __iter__(self):
        print('ImageScanner.__iter__: {}'.format(self._was_read))
        while True:
            try:
                yield self.read_bit()
            except StopIteration:
                return

    @property
    def info(self):
        """ The meta info for the QR code. Reads the code on access if needed.
        :rtype: QRCodeInfo
        """
        # print('Scanner.info: {}'.format(self._was_read))
        # if not self._was_read:
        #     self.read()
        return self._info

    def parseImage(self):
        print('ImageScanner.parseImage: {}'.format(self._was_read))
        # self._was_read = True
        self.read_info()
        # print(f'self: {self.__dict__}')
        self.data = validate_data(self._read_all_data(), self.info.version, self.info.error_correction_level)
        self._data_len = len(self.data)
        self.reset()

    def get_mask(self):
        print('ImageScanner.get_mask: {}'.format(self._was_read))
        mask_func = get_mask_func(self.info.mask_id)
        return {(x, y): 1 if mask_func(y, x) else 0 for x in range(self.info.size) for y in range(self.info.size)}
    
    def read_info(self):
        print('ImageScanner.read_info: {}'.format(self._was_read))
        info = QRCodeInfo()
        info.canvas = self.get_image_borders()
        info.block_size = self.get_block_size(info.canvas[:2])      # Number of pixels per module
        info.size = int((info.canvas[2] - (info.canvas[0]) + 1) / info.block_size[0]) # Number of modules on horizontal line
        info.version = (info.size - 17) // 4    # QR code version
        print(f'**QR Code Version {info.version}')
        self._info = info
        self._read_format_information()
        ECL = {0: 'unk0',
               1: 'unk1',
               2: 'unk2',
               3: 'H'}
        print(f'**QR Error Correction Level {ECL[self.info.error_correction_level]}')
        print(f'**QR Mask ID {self.info.mask_id}')
        self.mask = self.get_mask()
        print(f'info: {info.__dict__}')
        return info
    
    def _get_pixel(self, coords):
        # print('ImageScanner._get_pixel: {}'.format(self._was_read))
        try:
            shade, alpha = self.image.getpixel(coords)
            return BLACK if shade < 128 and alpha > 0 else WHITE
        except IndexError:
            return WHITE

    def get_image_borders(self):
        # print('ImageScanner.get_image_borders: {}'.format(self._was_read))
        def get_corner_pixel(canvas_corner, vector, max_distance):
            for dist in range(max_distance):
                for x in range(dist + 1):
                    coords = (canvas_corner[0] + vector[0] * x, canvas_corner[1] + vector[1] * (dist - x))
                    if self._get_pixel(coords) == BLACK:
                        return coords
            raise QrImageRecognitionException(
                "Couldn't find one of the edges ({0:s}-{1:s})".format(('top', 'bottom')[vector[1] == -1],
                                                                      ('left', 'right')[vector[0] == -1]))

        max_dist = min(self.image.width, self.image.height)
        min_x, min_y = get_corner_pixel((0, 0), (1, 1), max_dist)                           # Top-left
        max_x, max_x_y = get_corner_pixel((self.image.width - 1, 0), (-1, 1), max_dist)
        max_y_x, max_y = get_corner_pixel((0, self.image.height - 1), (1, -1), max_dist)
        if max_x_y != min_y:
            raise QrImageRecognitionException('Top-left position pattern not aligned with the top-right one')
        if max_y_x != min_x:
            raise QrImageRecognitionException('Top-left position pattern not aligned with the bottom-left one')
        return min_x, min_y, max_x, max_y

    def get_block_size(self, img_start):
        """
        Returns the size in pixels of a single block.
        :param tuple[int, int] img_start: The topmost left pixel in the QR (MUST be black or dark).
        :return: A tuple of width, height in pixels of a block
        :rtype: tuple[int, int]
        """
        # print('ImageScanner.get_block_size: {}'.format(self._was_read))
        pattern_size = 7

        left, top = img_start
        block_height, block_width = None, None
        for i in range(1, (self.image.width - left) // pattern_size):
            if self._get_pixel((left + i * pattern_size, top)) == WHITE:
                block_width = i
                break
        for i in range(1, (self.image.height - top) // pattern_size):
            if self._get_pixel((left, top + i * pattern_size)) == WHITE:
                block_height = i
                break
        return block_width, block_height

    def _read_format_information(self):
        print('ImageScanner._read_format_information: {}'.format(self._was_read))
        '''
        Read 5 data bits and 10 BCH bits
        '''
        # Read both locations
        source_1 = (self._get_straight_bits((8, -7), 7, 'd') << 8) + self._get_straight_bits((-1, 8), 8, 'l')
        source_2 = (self._get_straight_bits((7, 8), 8, 'l', (1,)) << 8) + self._get_straight_bits((8, 0), 9, 'd', (6,))
        # FORMAT_INFO_MASK = 0b101010000010010
        format_info = validate_format_info(source_1 ^ FORMAT_INFO_MASK, source_2 ^ FORMAT_INFO_MASK)
        print('format information: {:b}'.format(format_info))
        print('format information: {:b}'.format(format_info >> 3))
        self.info.error_correction_level = ec_level_from_format_info_code(format_info >> 3)
        print('EC level: {}'.format(self.info.error_correction_level))
        self.info.mask_id = format_info & 0b111
        return

    def _read_all_data(self):
        print('ImageScanner._read_all_data: {}'.format(self._was_read))
        pos_iterator = QrZigZagIterator(self.info.size, get_dead_zones(self.info.version))
        return [self._get_bit(pos) ^ self.mask[pos] for pos in pos_iterator]

    def read_bit(self):
        # print('ImageScanner.read_bit: {}'.format(self._was_read))
        # if not self._was_read:
        #     self.read()
        self._current_index += 1
        if self._current_index >= self._data_len:
            self._current_index = self._data_len
            raise StopIteration()
        return self.data[self._current_index]

    def read_int(self, amount_of_bits):
        # print('Scanner.read_int: {}'.format(self._was_read))
        # if not self._was_read:
        #     self.read()
        val = 0
        bits = [self.read_bit() for _ in range(amount_of_bits)]
        for bit in bits:
            val = (val << 1) + bit
        return val

    def _get_bit(self, coords):
        # print('ImageScanner._get_bit: {}'.format(self._was_read))
        x, y = coords
        if x < 0:
            x += self.info.size
        if y < 0:
            y += self.info.size
        return self._get_pixel(tuples.add(self.info.canvas[:2], tuples.multiply((x, y), self.info.block_size)))

    def _get_straight_bits(self, start, length, direction, skip=()):
        """
        Reads several bits from the specified coordinates
        :param tuple[int] start: The x, y of the start position
        :param int length: the amount of bits to read
        :param str direction: d(own) or l(eft)
        :param tuple skip: the indexes to skip. they will still be counted on for the length
        :return: The bits read as an integer
        :rtype: int
        """
        # print('ImageScanner._get_straight_bits: {}'.format(self._was_read))
        result = 0
        counted = 0
        step = (0, 1) if direction == 'd' else (-1, 0)
        for i in range(length):
            if i in skip:
                start = tuples.add(start, step)
                continue
            result += self._get_bit(start) << counted
            counted += 1
            start = tuples.add(start, step)
        return result


class QrZigZagIterator(Iterator):
    def __init__(self, size, dead_zones):
        self.size = size
        self.ignored_pos = {(x, y) for zone in dead_zones
                            for x in range(zone[0], zone[2] + 1)
                            for y in range(zone[1], zone[3] + 1)}
        self._current = ()
        self._scan_direction = 'u'
        self._odd_col_modifier = False
        self.reset()

    def reset(self):
        self._current = (self.size - 2, self.size)
        self._scan_direction = 'u'
        self._odd_col_modifier = False

    def _advance_pos(self):
        pos = self._current
        while pos[0] >= 0 and (pos == self._current or pos in self.ignored_pos):
            step = (-1, 0)
            # We advance a line if we're in an odd column, but if we have the col_modified flag on, we switch it around
            advance_line = ((self.size - pos[0]) % 2 == 0) ^ self._odd_col_modifier
            if advance_line:
                step = (1, -1 if self._scan_direction == 'u' else 1)
                # if we're trying to advance a line but we've reached the edge, we should change directions
                if (pos[1] == 0 and self._scan_direction == 'u') or \
                        (pos[1] == self.size - 1 and self._scan_direction == 'd'):
                    # swap scan direction
                    self._scan_direction = 'd' if self._scan_direction == 'u' else 'u'
                    # go one step left
                    step = (-1, 0)
                    # make sure we're not tripping over the timing array
                    if pos[0] > 0 and all((pos[0] - 1, y) in self.ignored_pos for y in range(self.size)):
                        step = (-2, 0)
                        self._odd_col_modifier = not self._odd_col_modifier
            pos = tuples.add(pos, step)
        self._current = pos

    def __next__(self):
        self._advance_pos()
        if self._current[0] < 0:
            raise StopIteration()
        return self._current

    next = __next__


class QRCodeInfo(object):
    # number between 1-40
    version = 0

    # the error correction level.
    error_correction_level = 0

    # the id of the mask (0-7)
    mask_id = 0

    # the part of the image that contains the QR code
    canvas = (0, 0)

    # the size of each block in pixels
    block_size = (0, 0)

    # the amount of blocks at each side of the image (it's always a square)
    size = 0

    def __str__(self):
        return '<version %s, ec %s, mask %s>' % \
               (self.version, self.error_correction_level, self.mask_id)
