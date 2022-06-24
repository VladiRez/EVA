"""Part of the project AI-in-Orbit Factory, 
Fachbereich Datenverarbeitung in der Konstruktion,
Technische Universität Darmstadt, Germany
Author: Robert Knobloch, TU Darmstadt, robert.knobloch@stud.tu-darmstadt.de

The command line interface for interacting with the standalone marker detection 
gui for the AIIOF Project
python cli.py --help

"""

import sys
import pathlib
import argparse
# Adds project directory to python path
sys.path.append(pathlib.Path(__file__).parent.resolve())

from scripts import make_markers
from scripts import md_gui
from scripts import md_daemon


# Create main parser, and a subparser for each program function
parser = argparse.ArgumentParser(description="Command-Line Interface for the AI-in-Orbit Factory")
subparsers = parser.add_subparsers(dest="subparser")
sp_make_charuco = subparsers.add_parser("make-charuco", help="Create a charuco board")
sp_make_aruco = subparsers.add_parser("make-aruco", help="Create an AruCo marker")
sp_run = subparsers.add_parser("run", help="""
            Run AruCo marker detection, either in GUI mode or as a daemon with zeromq messaging""")

sp_make_charuco.add_argument("squares-x", metavar="Nx", type=int, 
                            help="Number of squares on the x-axis")
sp_make_charuco.add_argument("squares-y", metavar="Ny", type=int,
                            help="Number of squares on the y-axis")
sp_make_charuco.add_argument("width-square", type=float, 
                            help="Width of a charuco square in meters")
sp_make_charuco.add_argument("width-marker", type=float, 
                            help="Width of a charuco marker in meters")
sp_make_charuco.add_argument("dict", type=str, help="AruCo dictionary to use (DICT_xXx_xxx)")

sp_make_aruco.add_argument("id", type=int, help="AruCo marker ID")
sp_make_aruco.add_argument("dict", type=str, help="AruCo dictionary to use (DICT_xXx_xxx)")

sp_run.add_argument("--gui", dest="gui", action="store_true", help="Start GUI (default: False)")
sp_run.set_defaults(gui=False)
sp_run.add_argument("--zmq", dest="zmq", action="store_true", help="Start with ZeroMQ Server (default: False)")
sp_run.set_defaults(zmq=False)
sp_run.add_argument("-i", "--ip", dest="ip", type=str, default="localhost", help="Specify ZeroMQ TCP connection IP")
sp_run.add_argument("-p", "--port", dest="port", type=int, default=3777, help="Specify ZeroMQ TCP connection port")
sp_run.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Show more info")
sp_run.set_defaults(verbose=False)

# Convert parser arguments to dictionary
args = vars(parser.parse_args())

# Execute relevant scipts
if args["subparser"] == "make-aruco":
    make_markers.make_aruco(args)
elif args["subparser"] == "make-charuco":
    make_markers.make_charuco(args)
elif args["subparser"] == "run":
    if(args["gui"] == True):
        md_gui.main(args)
    else:
        md_daemon.main(args)