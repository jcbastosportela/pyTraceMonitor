import numpy as np
from abc import ABC, abstractmethod
import struct
import sys
import datetime

TC_ERROR = 0x80		#Trace is an error message
TC_LF = 0x40		#Trace includes a line feed at the end
TC_ASCII = 0x01		#Trace one ASCII character

TC_INT8D = 0x02		#Trace a signed one byte integer value decimal
TC_UINT8D = 0x03		#Trace an unsigned one byte integer value decimal
TC_UINT8H = 0x04		#Trace an unsigned one byte integer value hexadecimal

TC_INT16D = 0x05		#Trace a signed two byte integer value decimal
TC_UINT16D = 0x06		#Trace an unsigned two byte integer value decimal
TC_UINT16H = 0x07		#Trace an unsigned two byte integer value hexadecimal

TC_INT32D = 0x08		#Trace a signed four byte integer value decimal
TC_UINT32D = 0x09		#Trace an unsigned four byte integer value decimal
TC_UINT32H = 0x0A		#Trace an unsigned four byte integer value hexadecimal

TC_FLOAT16 = 0x0B		#Trace a two byte float value (KNX format)
TC_FLOAT32 = 0x0C		#Trace a four byte float value (IEEE)

TC_STRING = 0x0D		#Trace a zero terminated string
TC_TEXT = 0x0E		#Trace a text ID combined of module ID and line number

command_map = {}

ugly_start_of_line_flag = True


class DataParserBase(ABC):
    @property
    def nBytes(self):
        return self.__n_bytes
        pass

    def __init__(self, command, n_bytes=0 ):
        self.__n_bytes = n_bytes
        self.value_raw = bytes()
        self.eol = ''
        if (command & TC_LF) == TC_LF:
            self.eol = '\n'
        self.msgtype = sys.stdout
        if (command & TC_ERROR) == TC_ERROR:
            self.msgtype = sys.stderr

    @abstractmethod
    def process(self, val):
        pass

    def trace(self, msg):
        global ugly_start_of_line_flag
        if ugly_start_of_line_flag:
            print('{} - '.format(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")), file=self.msgtype, end='')

        ugly_start_of_line_flag = False
        if self.eol == '\n' or msg.endswith('\n'):
            ugly_start_of_line_flag = True

        print('{}'.format(msg),
          file=self.msgtype,
          end=self.eol)

class DataParserNumberBase(DataParserBase):
    def __init__(self, command, n_bytes):
        super().__init__(command, n_bytes)
        self.value = 0
        if n_bytes <= 2:
            self.endianess = 'big'
        else:
            self.endianess = 'little'

    def processNumber(self, val):
        self.value_raw += val
        if self.value_raw.__len__() == self.nBytes:
            self.value = int.from_bytes(self.value_raw, self.endianess)
            return True
        else:
            return False


class Parser:
    #map_dict = None

    def __init__(self, _map_dict):
        self.__cmd = None
        self.map_dict = _map_dict
        self.dispatch = {
            TC_ASCII :      [Parser.ParserASCII, '{}'],# 0x01
            TC_INT8D :      [Parser.ParserInt8, '{}'],# 0x02
            TC_UINT8D :     [Parser.ParserUint8, '{}'],# 0x03
            TC_UINT8H :     [Parser.ParserInt8, '{:02X}'],# 0x04
            TC_INT16D :     [Parser.ParserInt16, '{}'],# 0x05
            TC_UINT16D :    [Parser.ParserUint16, '{}'],# 0x06
            TC_UINT16H :    [Parser.ParserUint16, '{:02X}'],# 0x07
            TC_INT32D :     [Parser.ParserInt32, '{}'],# 0x08
            TC_UINT32D :    [Parser.ParserUint32, '{}'],# 0x09
            TC_UINT32H :    [Parser.ParserUint32, '{:02X}'],# 0x0A
            TC_FLOAT16 :    [Parser.ParserFloat16, '{e}'],# 0x0B
            TC_FLOAT32 :    [Parser.ParserFloat32, '{:f}'],# 0x0C
            TC_STRING :     [Parser.ParserString, '{}'],# 0x0D
            TC_TEXT :       [Parser.ParserText, self.map_dict, '{}']# 0x0E
        }

    def process(self, data):
        try:
            if self.__cmd is None:
                cmd = (data[0] & 0x3F)
                if cmd in self.dispatch:
                    args = (self.dispatch[cmd][1:])
                    self.__cmd = self.dispatch[cmd][0](data[0], *args)
                else:
                    print('Not synced')
                    #self.__cmd = DataParserBase
            else:
                try:
                    if self.__cmd.process(data):
                        self.__cmd = None
                except Exception as ex:
                    print('{}'.format(ex))
                    self.__cmd = None
        except Exception as ex:
            print('error {}'.format(ex))
            self.__cmd = None
            pass

    class ParserText(DataParserNumberBase):
        def __init__(self, command, map_dict, fmt='{}'):
            super().__init__(command, 4)
            self.__format = fmt
            self.code = bytes()
            self.value_raw += b'\0'
            self.map_dict = map_dict

        def process(self, val):
            if self.processNumber(val):
                code = struct.unpack('>i', self.value_raw)[0]
                if code in self.map_dict:
                    self.trace(self.__format.format(self.map_dict[code].replace('\n', '').replace('\\n', '\n')))
                else:
                    print('Unknown code: {:X}'.format(code))
                return True
            else:
                return False

    class ParserInt8(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 1)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(np.int8(self.value)))
                return True
            else:
                return False

    class ParserUint8(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 1)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(np.uint8(self.value)))
                return True
            else:
                return False

    class ParserInt16(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 2)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(np.int16(self.value)))
                return True
            else:
                return False

    class ParserUint16(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 2)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(np.uint16(self.value)))
                return True
            else:
                return False

    class ParserInt32(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 4)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(np.int32(self.value)))
                return True
            else:
                return False

    class ParserUint32(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 4)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(np.uint32(self.value)))
                return True
            else:
                return False

    class ParserFloat16(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 2)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(struct.unpack('<e', self.value_raw)[0]))
                return True
            else:
                return False

    class ParserFloat32(DataParserNumberBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 4)
            self.__format = fmt

        def process(self, val):
            if self.processNumber(val):
                self.trace(self.__format.format(struct.unpack('<f', self.value_raw)[0]))
                return True
            else:
                return False

    class ParserASCII(DataParserBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, 1)
            self.__format = fmt

        def process(self, val):
            """
            Process
            :param val: the value to process
            :type val: byte
            :return:
            """
            self.trace(self.__format.format(val.decode('ascii')))
            return True

    class ParserString(DataParserBase):
        def __init__(self, command, fmt='{}'):
            super().__init__(command, -1)
            self.__format = fmt

        def process(self, val):
            """
            Process
            :param val: the value to process
            :type val: byte
            :return:
            """
            self.value_raw += val
            if val[0] == 0:
                self.trace(self.__format.format(self.value_raw.decode('ascii')))
                return True
            else:
                return False


#command_map[TC_INT16D] = parser_print16