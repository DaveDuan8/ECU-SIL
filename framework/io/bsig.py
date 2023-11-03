"""
framework/io/bsig
-----------

Binary Signal Read Class

**replaced by `SignalReader` and `SignalWriter`!**

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:12:40CEST $
"""
# pylint: skip-file
# - imports -----------------------------------------------------------------------------------------------------------
from ctypes import c_int8, memmove, c_float, c_uint8, c_double, byref, c_int16, c_uint16, c_int32, c_int64, \
    c_uint32, c_uint64
import os
import struct
import zlib

DEFAULT_SIGNATURE = 'BIN\0'
HDR_SIZE = 24
MAX_VERSION = {'Major': 1, 'Minor': 1, 'Patch': 0}


def type_to_size(s_type):
    """conversation from type to size"""
    if s_type == 0:  # Unknown
        return -1
    elif s_type == 1:  # U8
        return 1
    elif s_type == 2:  # I8
        return 1
    elif s_type == 3:  # U16
        return 2
    elif s_type == 4:  # I16
        return 2
    elif s_type == 5:  # U32
        return 4
    elif s_type == 6:  # I32
        return 4
    elif s_type == 7:  # U64
        return 8
    elif s_type == 8:  # I64
        return 8
    elif s_type == 9:  # FLT
        return 4
    elif s_type == 10:  # DBL
        return 8

# - classes -----------------------------------------------------------------------------------------------------------


class BSigFileIO(file):
    """
    Class for Binary Signal File Read. (\*.bsig)

    Base class for File I/O Handling and conversion of Signal Data

    :note:          usage : ...

    :author:        Robert Hecker
    """
    def __init__(self, filename, mode):
        file.__init__(filename, mode)

    def __del__(self):
        pass

    def read_sig(self, s_type):

        if s_type == 0:  # Unknown
            return self.read_ui8()
        elif s_type == 1:  # U8
            return self.read_ui8()
        elif s_type == 2:  # I8
            return self.read_i8()
        elif s_type == 3:  # U16
            return self.read_ui16()
        elif s_type == 4:  # I16
            return self.read_i16()
        elif s_type == 5:  # U32
            return self.read_ui32()
        elif s_type == 6:  # I32
            return self.read_i32()
        elif s_type == 7:  # U64
            return self.read_ui64()
        elif s_type == 8:  # I64
            return self.read_i64()
        elif s_type == 9:  # FLT
            return self.read_flt()
        elif s_type == 10:  # DBL
            return self.read_dbl()

    def read_str(self):
        """
        Read String Len
        """
        # Read String
        return self.read(struct.unpack('L', self.read(4))[0])

    def read_ui8(self):
        """
        Read unsigned char
        """
        return struct.unpack('B', self.read(1))[0]

    def read_i8(self):
        """
        Read signed char
        """
        return struct.unpack('b', self.read(1))[0]

    def read_ui16(self):
        """
        Read unsigned short
        """
        return struct.unpack('H', self.read(2))[0]

    def read_i16(self):
        """
        Read signed short
        """
        return struct.unpack('h', self.read(2))[0]

    def read_ui32(self):
        """
        Read unsigned long
        """
        return struct.unpack('L', self.read(4))[0]

    def read_i32(self):
        """
        Read signed long
        """
        return struct.unpack('l', self.read(4))[0]

    def read_ui64(self):
        """
        Read unsigned __int64
        """
        return struct.unpack('Q', self.read(8))[0]

    def read_i64(self):
        """
        Read signed __int64
        """
        return struct.unpack('q', self.read(8))[0]

    def read_dbl(self):
        """
        Read double
        """
        return struct.unpack('d', self.read(8))[0]

    def read_flt(self):
        """
        Read float
        """
        return struct.unpack('f', self.read(4))[0]


class BSig100(object):
    """
    Class for Binary Signal File Read. (\*.bsig)

    Class for Reading Binary Signal Files Version 1.0.0

    :note:          usage : ...

    :author:        Robert Hecker
    """
    def __init__(self, bsig_100):
        """
        Initialize all unused Variables
        """
        self.__f = bsig_100
        self.__num_signals = 0
        self.__data_offset = 0
        self.__data = {}
        self.__data2 = []
        self._num_rows = 0
        self.__rowsize = 0
        self.__startoffset = 0

    def __del__(self):
        pass

    def __read_signal_hdr_blk(self):
        """ReadSignalName
        """
        name = self.__f.read_str()

        # ReadSignalSize
        size = self.__f.read_ui32()

        # Read Signal Type
#        s_type = self.__f.read_ui8()

        jumplen = 0

        self.__data[name] = [size, type, self.__startoffset, jumplen]
        self.__data2.append(name)
        self.__startoffset += size  # type_to_size(type)

    def read_file_header(self):
        """Read Number of Signals
        """
        self.__num_signals = self.__f.read_ui64()
        self.__startoffset = 0

        for _ in range(0, self.__num_signals):
            self.__read_signal_hdr_blk()

        # Remember current File Pos
        self.__data_offset = self.__f.tell()

        self.__f.seek(0, 2)
        size = self.__f.tell()
        self.__f.seek(self.__data_offset)

        for item in self.__data:
            self.__rowsize = self.__rowsize + self.__data[item][0]

        # Calculate Jumplen
        for item in self.__data2:
            self.__data[item][3] = self.__rowsize - self.__data[item][0]

        self._num_rows = (size - self.__data_offset) / self.__rowsize

    def get_num_signals(self):
        return self.__num_signals

    def get_signal_name(self, idx):
        return self.__data2[idx]

    def get_signal_by_name(self, name):
        data = []
        jumplen = self.__data[name][3]
#        s_type = self.__data[name][1]

        # Go to start of Data Section
        self.__f.seek(self.__data_offset + self.__data[name][2])

        for _ in range(0, self._num_rows):
            # Read Data Element
            if self.__data[name][0] > type_to_size(type):
                tmp = []
                for __ in range(0, self.__data[name][0] / type_to_size(type)):
                    tmp.append(self.__f.read_sig(type))
                data.append(tmp)
            else:
                data.append(self.__f.read_sig(type))
            # Jump to Next Element
            self.__f.seek(jumplen, 1)

        return data

    def get_signal_by_index(self, idx):
        return self.get_signal_by_name(self.__data2[idx])

    def get_signals_by_list(self, names):

        data = []
        for item in names:
            data.append(self.get_signal_by_name(item))

        return data


# try:
#     from exceptions import StandardError as _BaseException
# except ImportError:
#     _BaseException = Exception


class Bsig200Exception(StandardError):
    """bsig200 exception"""
    def __init__(self, description):
        self.__description = str(description)

    def __str__(self):
        errror_description = "=====================================================\n"
        errror_description += "ERROR: " + self.__description
        errror_description += "\n=====================================================\n"
        return str(errror_description)

    def description(self):
        return self.__description


class BSig200(object):
    """Class constructor.
    """
    def __init__(self):
        self.__block_size = 0
        self.__file_size = 0
        self.__hdr_size = 0
        self.__hdr_offset = 0
        self.__signals_count = 0
        self.__index_table_size = 0
        self.__index_table_offset = 0
        self.__index_table = None
        self.__f = None
        self.__file_name = ''
        self.__signal_data = []
        self.__compression = False
        self.__version = {'Major': 0, 'Minor': 0, 'Patch': 0}

    def __del__(self):
        self.close()

    @staticmethod
    def read_file_header():
        """ Just for compatibility with bsig_100
        """
        pass

    @staticmethod
    def __get_signal_format_str(s_type):
        """Function returns the format string needed for unpacking the binary data.

        :param s_type: The type of the signal. The values match eDataType define in
                     CSignalData as defined in gex_datawriterifc.h.
        """
        if s_type == 32776:
            return 'b'
        elif s_type == 32784:
            return 'h'
        elif s_type == 32800:
            return 'l'
        elif s_type == 32832:
            return 'q'
        elif s_type == 8:
            return 'B'
        elif s_type == 16:
            return 'H'
        elif s_type == 32:
            return 'L'
        elif s_type == 64:
            return 'Q'
        elif s_type == 36880:
            return 'f'
        elif s_type == 36896:
            return 'd'
        else:
            raise Bsig200Exception("Unknown format.")

    @staticmethod
    def __get_signal_type_size(s_type):
        """Function returns the size of a signal sample with the specified type.

        :param s_type: The type of the signal. The values match eDataType define
                     in CSignalData as defined in gex_datawriterifc.h
        """
        if s_type == 32776:
            return 1
        elif s_type == 32784:
            return 2
        elif s_type == 32800:
            return 4
        elif s_type == 32832:
            return 8
        elif s_type == 8:
            return 1
        elif s_type == 16:
            return 2
        elif s_type == 32:
            return 4
        elif s_type == 64:
            return 8
        elif s_type == 36880:
            return 4
        elif s_type == 36896:
            return 8
        else:
            raise Bsig200Exception("Unknown format.")

    def __read_i8(self, count=1):
        """Function reads and returns the specified count of i8 items.

       :param count: The number of items to read. By default 1 item will be read.
       """
        value = []
        fmt = 'b'
        try:
            for _ in range(count):
                bin_data = self.__f.read(1)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An error occured while unpacking binary data.")
        return value

    def __read_ui8(self, count=1):
        """Function reads and returns the specified count of ui8 items.

       :param count: The number of items to read. By default 1 item will be read.
       """
        value = []
        fmt = 'B'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(1)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An error occured while unpacking binary data.")
        return value

    def __read_i16(self, count=1):
        """Function reads and returns the specified count of i16 items.

       :param count: The number of items to read. By default 1 item will be read.
       """
        value = []
        fmt = 'h'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(2)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An error occured while unpacking binary data.")
        return value

    def __read_ui16(self, count=1):
        """Function reads and returns the specified count of ui16 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'H'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(2)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An error occured while unpacking binary data.")
        return value

    def __read_i32(self, count=1):
        """Function reads and returns the specified count of i32 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'i'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(4)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An error occured while unpacking binary data.")
        return value

    def __read_ui32(self, count=1):
        """Function reads and returns the specified count of ui32 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'I'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(4)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An occured while unpacking binary data.")
        return value

    def __read_i64(self, count=1):
        """Function reads and returns the specified count of i64 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'q'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(8)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An occured while unpacking binary data.")
        return value

    def __read_ui64(self, count=1):
        """Function reads and returns the specified count of ui64 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'Q'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(8)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An occurred while unpacking binary data.")
        return value

    def __read_f32(self, count):
        """Function reads and returns the specified count of f32 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'f'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(4)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An occurred while unpacking binary data.")

    def __read_f64(self, count):
        """Function reads and returns the specified count of i8 items.

        :param count: The number of items to read. By default 1 item will be read.
        """
        value = []
        fmt = 'd'
        try:
            for _ in xrange(count):
                bin_data = self.__f.read(8)
                value.append(struct.unpack(fmt, bin_data)[0])
        except:
            raise Bsig200Exception("An occurred while unpacking binary data.")

    def __read_block(self, abs_offset, size):
        """Function reads and returns a block of data from the file.

        :param abs_offset: Offset relative to the beginning of the file.
        :param size: The size of the block.
        :return: The block of data as a str object.
        """

        try:
            self.__f.seek(abs_offset)
            result = self.__f.read(size)
        except:
            raise Bsig200Exception("An occured while reading the binary file.")

        return result

    @staticmethod
    def __check_version(file_version):
        if not isinstance(file_version, dict):
            return False
        else:
            if file_version['Major'] < MAX_VERSION['Major']:
                return True
            elif file_version['Major'] == MAX_VERSION['Major']:
                if file_version['Minor'] <= MAX_VERSION['Minor']:
                    return True
                else:
                    # Patch should not matter only for bug fixes.
                    # if the file format is changed Minor should be incremented.
                    return False
            else:
                return False

    def __is_valid_file(self):
        """Function tests the file specified in the open function to see if it is a valid binary file.
        :return: True or False depending whether the file is valid or not.
        """
        self.__f.seek(0, os.SEEK_END)
        self.__file_size = self.__f.tell()
        if self.__file_size == 0:
            return False
        self.__f.seek(self.__file_size - HDR_SIZE)
        try:
            self.__signals_count = self.__read_ui32()[0]
            self.__block_size = self.__read_ui32()[0]
            self.__hdr_size = self.__read_ui32()[0]
            self.__index_table_size = self.__read_ui32()[0]
            bin_data = self.__read_ui8(3)
            self.__version['Major'] = bin_data[0]
            self.__version['Minor'] = bin_data[1]
            self.__version['Patch'] = bin_data[2]
            if self.__check_version(self.__version) is False:
                return False
            self.__compression = self.__read_ui8()[0]

            bin_data = self.__read_block(self.__f.tell(), 4)
        except OSError:
            return False
        if bin_data != DEFAULT_SIGNATURE:
            return False
        return True

    def __read_next_signal_info(self):
        """Function reads signal information.
        :return: A dictionary with signal information.
        """
        try:
            signal_name_len = self.__read_ui16()[0]
            signal_name = self.__read_block(self.__f.tell(), signal_name_len)
            array_len = self.__read_ui32()[0]
            s_type = self.__read_ui32()[0]
        except:
            raise Bsig200Exception("An error occurred while reading signal information.")
        return {'SignalName': signal_name, 'SignalType': s_type, 'ArrayLength': array_len,
                'Offsets': [], 'SampleCount': 0}

    def __read_signal_offsets(self, signal):
        """Function reads signal data offsets.
        :param signal: The signal for which to read the offsets.
        """
        try:
            offset_count = self.__read_ui32()[0]
            signal['SampleCount'] = self.__read_ui32()[0]
            signal['Offsets'] = self.__read_ui32(offset_count)
        except:
            raise Bsig200Exception("An exception occured while reading signal offsets.")

    def __read_file_data(self):
        """Function reads the data in the binary file such as signal information and offsets for the signals.
        :return: True or False depending of the success.
        """
        self.__hdr_offset = self.__file_size - HDR_SIZE - self.__hdr_size
        self.__index_table_offset = self.__hdr_offset - self.__index_table_size
        if self.__hdr_offset <= 0 or self.__index_table_offset <= 0:
            return False

        self.__f.seek(self.__hdr_offset)
        try:
            for _ in xrange(self.__signals_count):
                self.__signal_data.append(self.__read_next_signal_info())
        except OSError:
            return False

        self.__f.seek(self.__index_table_offset)
        try:
            for signal in self.__signal_data:
                self.__read_signal_offsets(signal)
        except OSError:
            return False
        return True

    def __clear(self):
        """Function clears the class variables.
        """
        self.__block_size = 0
        self.__file_size = 0
        self.__hdr_size = 0
        self.__hdr_offset = 0
        self.__index_table_size = 0
        self.__index_table_offset = 0
        self.__signals_count = 0
        self.__file_name = ''
        self.__index_table = None
        self.__f = None
        self.__version = None
        self.__version = {'Major': 0, 'Minor': 0, 'Patch': 0}
        self.__compression = False
        for i in xrange(len(self.__signal_data)):
            self.__signal_data[i] = None
        self.__signal_data = []

    def open(self, file_name):
        """Function opens the specified binary file.
        :param file_name: The path to the binary file.
        """
        if self.__f is not None:
            raise Bsig200Exception("A binary file is already opened.")
        if not isinstance(file_name, str):
            raise Bsig200Exception("Expecting str type as file name.")
        self.__file_name = file_name
        if os.path.exists(self.__file_name) is not True:
            raise Bsig200Exception('The path %s not found.' % self.__file_name)
        self.__f = open(self.__file_name, "rb")
        if self.__f is None:
            raise Bsig200Exception('The file %s could not be opened.' % self.__file_name)
        if self.__is_valid_file() is False:
            self.close()
            raise Bsig200Exception('The file %s is not a valid binary file.' % self.__file_name)
        if self.__read_file_data() is False:
            self.close()
            raise Bsig200Exception('The file %s is not a valid binary file.Possible corruption of data.' %
                                   self.__file_name)

    def close(self):
        """Function reads signal information.
        :return: A dictionary with signal information.
        """
        if self.__f is not None:
            try:
                self.__f.close()
            except:
                raise Bsig200Exception("An occured while closing the file.")
        self.__clear()

    def get_num_signals(self):
        """Function returns the number of signals in the binary file.
        :return: The number of signals in the binary file.
        """
        if self.__f is not None:
            return self.__signals_count
        else:
            return 0

    def get_signal_name(self, idx):
        """Function returns the name of the signal with the specified index.
        :param idx: The index of the signal.
        :return: The name of the signal if it exists.
        """
        if self.__f is None:
            raise Bsig200Exception("No file currently opened.")
        if type(idx) != int:
            raise Bsig200Exception("Expecting type int and found %s " % type(idx).__name__)
        try:
            return self.__signal_data[idx]['SignalName']
        except:
            raise Bsig200Exception("Signal index out of bounds.")

    def __read_signal_data(self, signal):
        """Function reads all the signal data merging all the block in the binary file.
        :param signal: The signal for which to read the data.
        :return: The data for the signal as a str object.
        """
        signal_data = {'Data': "", 'Size': 0}
        try:
            for offset in signal['Offsets']:
                if self.__compression != 0:
                    self.__f.seek(offset)
                    block_size = self.__read_ui32(1)[0]
                    temp_data = self.__read_block(offset + 4, block_size)
                    signal_data['Data'] += zlib.decompress(temp_data)
                else:
                    signal_data['Data'] += self.__read_block(offset, self.__block_size)
                signal_data['Size'] += self.__block_size
            return signal_data
        except:
            raise Bsig200Exception("An occurred while reading signal data for signal %s " % signal['SignalName'])

    def __read_signal_block(self, block_offset):
        """reads a signal block"""
        if self.__compression != 0:
            self.__f.seek(block_offset)
            block_size = self.__read_ui32(1)[0]
            temp_data = self.__read_block(block_offset + 4, block_size)
            current_block = zlib.decompress(temp_data)
        else:
            current_block = self.__read_block(block_offset, self.__block_size)
        return current_block

    def __process_signal_data_block(self, signal, offset, sample_count):

        """Function processes all the signal data.
        :param signal: The signal for which to process the data.
        :param offset: The offset for the signal.
        :param sample_count: The sample count for the signal.
        :return:  The processed data as a list with values. If the signal is
                  an array the returned list will have list with each sample value.
        """
        if offset < 0 or sample_count < 0:
            raise Bsig200Exception("An invalid offset or number of samples were specified  for signal %s " %
                                   signal['SignalName'])

        type_size = self.__get_signal_type_size(signal['SignalType'])
        fmt_str = self.__get_signal_format_str(signal['SignalType'])
        sample_size = type_size * signal['ArrayLength']

        if sample_count > signal['SampleCount'] - offset:
            sample_count = signal['SampleCount'] - offset
        else:
            sample_count = sample_count

        start_block_index = (offset * sample_size) / self.__block_size
        start_block_offset = (offset * sample_size) % self.__block_size

        if(offset + sample_size * sample_count) % self.__block_size:
            end_block_index = ((offset * sample_size + sample_size * sample_count) / self.__block_size) + 1
        else:
            end_block_index = (offset * sample_size + sample_size * sample_count) / self.__block_size

#        end_offset = (Offset + sample_size * sample_count) % self.__block_size

        # current_block = ""
        # raw_data      = ""
        byte_size = sample_count * sample_size
        raw_data = (c_int8 * byte_size)
        raw_block_offset = 0
        raw_offset_data = byref(raw_data)

        try:
            # Merge all data for the samples from different blocks
            for block_offset in signal['Offsets'][start_block_index:end_block_index]:
                current_block = self.__read_signal_block(block_offset)
                current_block = current_block[start_block_offset:len(current_block)]
                start_block_offset = 0
                # raw_data += current_block
                block_byte_size = len(current_block)
                if raw_block_offset + block_byte_size > byte_size:
                    block_byte_size = byte_size - raw_block_offset
                    if block_byte_size <= 0:
                        break
                memmove(raw_offset_data, current_block, block_byte_size)
                raw_block_offset += block_byte_size
                raw_offset_data = byref(raw_data, raw_block_offset)
        except:
            raise Bsig200Exception("An occured while reading signal data block for signal %s " %
                                   signal['SignalName'])

        if signal['ArrayLength'] == 1:
            # count = sample_count

            if fmt_str == "f":
                signal_data = (c_float * sample_count)()
            elif fmt_str == "c":
                signal_data = (c_int8 * sample_count)()
            elif fmt_str == "b":
                signal_data = (c_int8 * sample_count)()
            elif fmt_str == "B":
                signal_data = (c_uint8 * sample_count)()
            elif fmt_str == "h":
                signal_data = (c_int16 * sample_count)()
            elif fmt_str == "H":
                signal_data = (c_uint16 * sample_count)()
            elif fmt_str == "l":
                signal_data = (c_int32 * sample_count)()
            elif fmt_str == "L":
                signal_data = (c_uint32 * sample_count)()
            elif fmt_str == "q":
                signal_data = (c_int64 * sample_count)()
            elif fmt_str == "Q":
                signal_data = (c_uint64 * sample_count)()
            elif fmt_str == "d":
                signal_data = (c_double * sample_count)()
            else:
                raise Bsig200Exception("Unknown format.")

            byte_size = sample_count * sample_size

            memmove(signal_data, raw_data, byte_size)

            data_list = signal_data[:]

            return data_list

        signal_data = []

        try:
            signal_samples = 0
            array_length = signal['ArrayLength']

            if fmt_str == "f":
                sample_value = (c_float * array_length)()
            elif fmt_str == "c":
                sample_value = (c_int8 * array_length)()
            elif fmt_str == "b":
                sample_value = (c_int8 * array_length)()
            elif fmt_str == "B":
                sample_value = (c_uint8 * array_length)()
            elif fmt_str == "h":
                sample_value = (c_int16 * array_length)()
            elif fmt_str == "H":
                sample_value = (c_uint16 * array_length)()
            elif fmt_str == "l":
                sample_value = (c_int32 * array_length)()
            elif fmt_str == "L":
                sample_value = (c_uint32 * array_length)()
            elif fmt_str == "q":
                sample_value = (c_int64 * array_length)()
            elif fmt_str == "Q":
                sample_value = (c_uint64 * array_length)()
            elif fmt_str == "d":
                sample_value = (c_double * array_length)()
            else:
                raise Bsig200Exception("Unknown format.")

            byte_size = array_length * type_size

            raw_block_offset = 0
            raw_offset_data = byref(raw_data)

            while signal_samples < sample_count:
                memmove(sample_value, raw_offset_data, byte_size)
                raw_block_offset += byte_size
                raw_offset_data = byref(raw_data, raw_block_offset)

                data_list = sample_value[:]

                signal_data.append(data_list)
                signal_samples += 1
        except:
            raise Bsig200Exception("An error occurred while processing signal data for signal %s " %
                                   signal['SignalName'])

        return signal_data

    def __process_signal_data(self, signal, data):
        """Function processes all the signal data.
        :param signal: The signal for which to process the data.
        :param data:   The data for the signal.
        :return:  The processed data as a list with values. If the signal is
                  an array the returned list will have list with each sample value.
        """
        offset = 0
        type_size = self.__get_signal_type_size(signal['SignalType'])
        fmt_str = self.__get_signal_format_str(signal['SignalType'])
        signal_samples = 0
        sample_value = []

        max_samples = signal['SampleCount']
        raw_data = data['Data']
        max_size = data['Size']

        try:
            if signal['ArrayLength'] == 1:
                type_size = self.__get_signal_type_size(signal['SignalType'])
                count = signal['SampleCount']

                if fmt_str == "f":
                    signal_data = (c_float * count)()
                elif fmt_str == "c":
                    signal_data = (c_int8 * count)()
                elif fmt_str == "b":
                    signal_data = (c_int8 * count)()
                elif fmt_str == "B":
                    signal_data = (c_uint8 * count)()
                elif fmt_str == "h":
                    signal_data = (c_int16 * count)()
                elif fmt_str == "H":
                    signal_data = (c_uint16 * count)()
                elif fmt_str == "l":
                    signal_data = (c_int32 * count)()
                elif fmt_str == "L":
                    signal_data = (c_uint32 * count)()
                elif fmt_str == "q":
                    signal_data = (c_int64 * count)()
                elif fmt_str == "Q":
                    signal_data = (c_uint64 * count)()
                elif fmt_str == "d":
                    signal_data = (c_double * count)()
                else:
                    raise Bsig200Exception("Unknown format.")

                byte_size = count * type_size

                if byte_size <= data['Size']:
                    memmove(signal_data, raw_data, byte_size)
                else:
                    raise Bsig200Exception("Samples count does not match. The binary file might be corrupted.")

                data_list = signal_data[:]

                return data_list

            else:
                signal_data = []  # [0]* signal['SampleCount']

                while signal_samples != max_samples and offset != max_size:
                    for _ in xrange(signal['ArrayLength']):
                        sample_value.append(struct.unpack_from(fmt_str, raw_data, offset)[0])
                        offset += type_size
                    signal_data.append(sample_value)
                    signal_samples += 1
                    sample_value = []
        except:
            raise Bsig200Exception("An error occurred while processing signal data for signal %s " %
                                   signal['SignalName'])

        if signal_samples != signal['SampleCount']:
            raise Bsig200Exception("Samples count does not match. The binary file might be corrupted.")
        return signal_data

    def get_signal_sample_count_by_index(self, idx):
        """Function returns the data for the signal with the specified index.
        :param idx: The index of the signal.
        :return: The signal data as a list.
        """
        if type(idx) != int:
            raise Bsig200Exception("Expecting type int and found %s" % type(idx).__name__)
        try:
            signal = self.__signal_data[idx]
        except:
            raise Bsig200Exception("Signal index out of bounds.")
        return signal['SampleCount']

    def get_signal_sample_count_by_name(self, signal_name):
        """Function returns the data for the signal with the specified index.
        :param signal_name: The name of the signal.
        :return: The signal data as a list.
        """
        for signal in self.__signal_data:
            if signal['SignalName'] == str(signal_name):
                return signal['SampleCount']
        raise Bsig200Exception("Signal '%s' could not be found in file." % signal_name)

    def get_signal_by_index(self, idx):
        """Function returns the data for the signal with the specified index.
        :param idx: The index of the signal.
        :return: The signal data as a list.
        """
        signal = None
        if type(idx) != int:
            raise Bsig200Exception("Expecting type int and found %s" % type(idx).__name__)
        try:
            signal = self.__signal_data[idx]
        except IndexError:
            Bsig200Exception("Signal index out of bounds.")
        return self.__process_signal_data(signal, self.__read_signal_data(signal))

    def get_signal_by_index2(self, idx, offset, sample_count):
        """Function returns the data for the signal with the specified index.
        :param idx: The index of the signal.
        :param offset: The offset for the signal.
        :param sample_count: The sample count for the signal.
        :return: The signal data as a list.
        """
        signal = None
        if type(idx) != int:
            raise Bsig200Exception("Expecting type int and found %s" % type(idx).__name__)
        try:
            signal = self.__signal_data[idx]
        except IndexError:
            Bsig200Exception("Signal index out of bounds.")
        return self.__process_signal_data_block(signal, offset, sample_count)
        # self.__process_signal_data(signal,self.__read_signal_data(signal))[Offset:Offset+SampleCount]

    def get_signal_by_name(self, signal_name):
        """Function returns the data for the signal with the specified index.
        :param signal_name: The name of the signal.
        :return: The signal data as a list.
        """
        for signal in self.__signal_data:
            if signal['SignalName'] == str(signal_name):
                return self.__process_signal_data(signal, self.__read_signal_data(signal))
        raise Bsig200Exception("Signal '%s' could not be found in file." % signal_name)

    def get_signal_by_name2(self, signal_name, offset, sample_count):
        """Function returns the data for the signal with the specified index.
        :param signal_name: The name of the signal.
        :param offset: The offset for the signal.
        :param sample_count: The sample count for the signal.
        :return: The signal data as a list.
        """
        for signal in self.__signal_data:
            if signal['SignalName'] == str(signal_name):
                return self.__process_signal_data_block(signal, offset, sample_count)
        raise Bsig200Exception("Signal '%s' could not be found in file." % signal_name)

    def get_signal_name_list(self):
        """Function returns the signal name in the binary file.
        :return: The signal names for the signals in the binary file or None if there is no binary file opened.
        """
        if self.__f is None:
            return None
        signal_name_list = []
        for signal in self.__signal_data:
            signal_name_list.append(signal['SignalName'])
        return signal_name_list

    def get_file_version(self):
        """Function returns the version of the binary format.
        :return: The version of the binary file format as a dictionary.
        """
        return self.__version

    def get_signals_by_list(self, names):
        """Function returns the values for the specified signals .
        :return: the values for the specified signals .
        """
        value_list = []
        for signal_name in names:
            try:
                signal_values = self.get_signal_by_name(signal_name)
            except Bsig200Exception, ex:
                raise ex
            value_list.append(signal_values)
        return value_list


"""
CHANGE LOG:
-----------
$Log: bsig.py  $
Revision 1.2 2020/03/31 09:12:40CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:12:07CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/io/project.pj

"""
