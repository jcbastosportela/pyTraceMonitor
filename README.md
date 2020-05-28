# pyTraceMonitor
A python3 version of Weinzierl's TraceMonitor (KNX development).
It can load the TraceMon generated .ini files and it can also create the map from the project folder (experimental)

## Why did I do this? Because:
- I have some developments in old KNX projects using Weinzierl's System7 KNX stack; this comes with some custom made tracing/debuging infrastucture tha requires TraceMon application (MSWindows) that parses source files looking for debug strings
- I program in GNU/Linux and TraceMon in wine doesn't work well (at least for me)
- I use eclipse based IDE and wanted to have the "debug terminal" (TraceMon like output) available inside Eclipse, maybe like an External Tool

So I decided to create firstly a python script capable of importing TraceMon .ini file (the map of trace/debug strings to their codes), connecting to the MCU's UART receiving the Trace commands and print the Trace/Debug strings according to map. I could run TraceMon with wine for parsing the project folder and saving the .ini map file. After I wanted to avoid having to open TraceMon for generating a new map everytime the code changes, so I implemented a very rudimentar parser wich looks for the project folder and builds the map; this seems to work. After I wanted this to automatically run when source files were changed, so I used 'watchdog' for checking for file changes.

## deps
see [requirements](requirements.txt)
