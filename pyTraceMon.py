#!/usr/bin/python3
import serial
from TMParser import parser as tm_parser
import os, sys, time
import argparse
import threading
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler


GB_stop = False

def read_map_from_file(path):
    """
    Creates a map of debug strings from an cache file. This is compatible with the files created by the TraceMon
    application from Weinzierl. The file must be a tab separated values file with first column being the debug code. 

    :param path: The path to the map file
    :type path: str
    :return: The map dictionary
    :rtype: dict
    """
    ret_map_dic = {}
    with open(path) as f:
        for line in f:
            if line.startswith('0x'):
                (key, val) = line.split(maxsplit=1)
                ret_map_dic[int(key, 0)] = val
    return ret_map_dic


def create_map_from_project(path):
    """
    Creates the debug strings map by parsing the project path.
    Note: This is experimental.

    :param path: Path to the path of the project with the source files
    :type path: str
    :return: The map dictionary
    :rtype: dict
    """
    print('Loading debug string map from path {}'.format(path))
    ret_map_dic = {}
        
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.c') or file.endswith('.cpp'):
                # print(os.path.join(root, file))
                with open(os.path.join(root, file), encoding="ISO-8859-1") as f:
                    for num, line in enumerate(f, 1):
                        if 'MODULE_ID' in line and '#define' in line:
                            module_id = eval(line.lstrip().rstrip().split()[2]) << 8 * 2
                        if 'TRACE_TEXT' in line:
                            text = line[line.find('"') + len('"'):line.rfind('"')].replace('\\t','\t')
                            ret_map_dic[module_id + num] = text
    return ret_map_dic


def run_trace_mon(serial_device, serial_baudrate, serial_parity, debug_strings_map, stop):
    """

    :param serial_device: The serial device to use /dev/tty...
    :param serial_baudrate: The baudrate for the serial communication
    :param serial_parity: The parity for the serial communication
    :param debug_strings_map: The debug string map (debug code <-> debug text string)
    :return: nothing
    """
    sys.stdout.flush()
    ser = serial.Serial(port=serial_device, baudrate=serial_baudrate, parity=serial_parity, timeout=1)

    com_parser = tm_parser.Parser(debug_strings_map)
    while not stop():
        rcvd = ser.read(1)
        if rcvd is not b'':
            com_parser.process(rcvd)
            sys.stdout.flush()


class PathChangesEventHandler(FileSystemEventHandler):
    def __init__(self, thread_trace_mon):
        super().__init__()
        self.thread_trace_mon = thread_trace_mon

    def on_change(self, event):
        if event.src_path.endswith('.c'):
            global GB_stop
            GB_stop = True
            self.thread_trace_mon.join()

    def on_moved(self, event):
        self.on_change(event)
        pass

    def on_created(self, event):
        self.on_change(event)
        pass

    def on_deleted(self, event):
        self.on_change(event)
        pass

    def on_modified(self, event):
        self.on_change(event)
        pass



def monitor_path(path, thread_trace_mon):
    event_handler = PathChangesEventHandler(thread_trace_mon)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while not GB_stop:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('path', help='Path to the map file or to the project top be parsed', )
    args_parser.add_argument('-d', '--device', required=True, help='Path to the serial device connected to the debug '
                                                                   'UART')
    args_parser.add_argument('-b', '--baudrate', default=460800, help='The baudrate of the serial communication of '
                                                                      'the debug')
    args_parser.add_argument('-p', '--parity', default=serial.PARITY_NONE, help='The parity ("N" none, "O" odd, "E" '
                                                                                'even) of the serial communication of '
                                                                                'the debug')

    args = args_parser.parse_args()

    map_dic = {}
    is_path = False
    if os.path.isfile(args.path):
        map_dic = read_map_from_file(args.path)
    else:
        is_path = True
        map_dic = create_map_from_project(args.path)

    try:
        while True:
            trace_mon_thread = threading.Thread(target=run_trace_mon, kwargs=dict(serial_device=args.device, serial_baudrate=args.baudrate, serial_parity=args.parity,
                          debug_strings_map=map_dic, stop=lambda: GB_stop))
            if is_path:
                GB_stop = False
                monitor_thread = threading.Thread(target=monitor_path, kwargs=dict(path=args.path, thread_trace_mon=trace_mon_thread))
                monitor_thread.start()
            trace_mon_thread.start()
            trace_mon_thread.join()
            if is_path:
                map_dic = create_map_from_project(args.path)
                monitor_thread.join()
    except KeyboardInterrupt:
        pass

    GB_stop = True
