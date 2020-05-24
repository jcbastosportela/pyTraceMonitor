import serial
from TMParser import parser
import os
import argparse


def read_map_from_file(path):
    """
    Creates a map of debug strings from an cache file. This is compatible with the files created by the TraceMon
    application from Weinzierl. The file must be a tab separated values file with first column being the debug code.

    :param path: The path to the map file
    :type path: str
    :return: The map dictionary
    :rtype: dict
    """
    map_dic = {}
    with open(path) as f:
        for line in f:
            if line.startswith('0x'):
                (key, val) = line.split(maxsplit=1)
                map_dic[int(key, 0)] = val
    return map_dic


def create_map_from_project(path):
    """
    Creates the debug strings map by parsing the project path.
    Note: This is experimental.

    :param path: Path to the path of the project with the source files
    :type path: str
    :return: The map dictionary
    :rtype: dict
    """
    map_dic = {}

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.c'):
                print(os.path.join(root, file))
                with open(os.path.join(root, file), encoding="ISO-8859-1") as f:
                    for num, line in enumerate(f, 1):
                        if 'MODULE_ID' in line and '#define' in line:
                            module_id = eval(line.lstrip().rstrip().split()[2]) << 8 * 2
                        if 'TRACE_TEXT' in line:
                            text = line[line.find('"') + len('"'):line.rfind('"')].replace('\\t', '\t').replace('\\n',
                                                                                                                '\n')
                            map_dic[module_id + num] = text
    return map_dic


def run_trace_mon(serial_device, serial_baudrate, serial_parity, map_dic):
    """

    :param serial_device: The serial device to use /dev/tty...
    :param serial_baudrate: The baudrate for the serial communication
    :param serial_parity: The parity for the serial communication
    :param map_dic: The debug string map (debug code <-> debug text string)
    :return: nothing
    """
    ser = serial.Serial(port=serial_device, baudrate=serial_baudrate, parity=serial_parity)

    com_parser = parser.Parser(map_dic)
    while True:
        com_parser.process(ser.read(1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='Path to the map file or to the project top be parsed', )
    parser.add_argument('-d', '--device', required=True, help='Path to the serial device connected to the debug UART')
    parser.add_argument('-b', '--baudrate', default=460800, help='The baudrate of the serial communication of the debug')
    parser.add_argument('-p', '--parity', default=serial.PARITY_NONE, help='The parity ("N" none, "O" odd, "E" even) of'
                                                                           'the serial communication of the debug')

    args = parser.parse_args()

    map_dic = {}
    if os.path.isfile(args.path):
        map_dic = read_map_from_file(args.path)
    else:
        map_dic = create_map_from_project(args.path)

    run_trace_mon(serial_device=args.device, serial_baudrate=args.baudrate, serial_parity=args.parity, map_dic=map_dic)
