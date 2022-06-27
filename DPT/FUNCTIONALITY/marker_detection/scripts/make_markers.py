"""Part of the project AI-in-Orbit Factory, 
Fachbereich Datenverarbeitung in der Konstruktion,
Technische Universität Darmstadt, Germany
Author: Robert Knobloch, TU Darmstadt, 
    robert.knobloch@stud.tu-darmstadt.de

A script to create AruCo markers.
Execute through cli.py interface

FUNCTIONS
---------
make_aruco(args: args: Dict[str, object]) -> None
    Create a custom AruCo marker from parser arguments and 
    store it in ../data/

make_charuco(args: args: Dict[str, object]) -> None
    Create custom ChAruCo board from parser arguments and 
    store it as charuco.png in ../data/
"""

from typing import Dict
import pathlib
import cv2 as cv
import numpy as np


# Make a dictionary for converting argument String to 
# the corresponding call function.
DICT_GETFUNCTIONS = {
        "DICT_4X4_50": cv.aruco.DICT_4X4_50,
        "DICT_4X4_100": cv.aruco.DICT_4X4_100,
        "DICT_4X4_250": cv.aruco.DICT_4X4_250,
        "DICT_4X4_1000": cv.aruco.DICT_4X4_1000,
        "DICT_5X5_50": cv.aruco.DICT_5X5_50,
        "DICT_5X5_100": cv.aruco.DICT_5X5_100,
        "DICT_5X5_250": cv.aruco.DICT_5X5_250,
        "DICT_5X5_1000": cv.aruco.DICT_5X5_1000,
        "DICT_6X6_50": cv.aruco.DICT_6X6_50,
        "DICT_6X6_100": cv.aruco.DICT_6X6_100,
        "DICT_6X6_250": cv.aruco.DICT_6X6_250,
        "DICT_6X6_1000": cv.aruco.DICT_6X6_1000,
        "DICT_7X7_50": cv.aruco.DICT_7X7_50,
        "DICT_7X7_100": cv.aruco.DICT_7X7_100,
        "DICT_7X7_250": cv.aruco.DICT_7X7_250,
        "DICT_7X7_1000": cv.aruco.DICT_7X7_1000, 
    }

def make_aruco(args: Dict[str, object]):
    """Create a custom AruCo marker and store it in ../data/

    Args:
        args (Dict[str, object]): dictionary containing the parser arguments, 
            needed are entries for 'id' and 'dict'
    """    
    try:
        aruco_dict = cv.aruco.getPredefinedDictionary(DICT_GETFUNCTIONS[args["dict"]])
    except KeyError:
        print("Unrecognized AruCo dictionary - check for spelling")
        raise
        
    print(f"Generating AruCo marker with ID {args['id']} from dictionary {args['dict']}")
        
    # Create empty image, draw marker
    marker = np.full((200, 200, 1), 0, dtype="uint8")
    cv.aruco.drawMarker(aruco_dict, args["id"], 200, marker, 1)

    # Get path to data folder
    save_path = pathlib.Path(__file__).parent.resolve() / ".." \
        / "cli_data" / "marker" / f"marker{args['id']}.png"

    # Save marker
    if cv.imwrite(str(save_path), marker) is True:
        print(f"Saved as marker{args['id']}.png in cli_data/marker/")
    else:
        print("Failed to create marker")

def make_charuco(args: Dict[str, object]):
    """Create custom ChAruCo board and store it as charuco.png in ../data/

    Args:
        args (Dict[str, object]): dictionary containing the parser arguments, 
            needed are entries for 'dict', 'squares-x', 'squares-y', 'width-square',
            'width-marker'
    """    
    try:
        aruco_dict = cv.aruco.getPredefinedDictionary(DICT_GETFUNCTIONS[args["dict"]])
    except KeyError:
        print("Unrecognized AruCo dictionary - check for spelling")
        raise
    
    # Create board
    board = cv.aruco.CharucoBoard_create(args["squares-x"], args["squares-y"], 
                                        args["width-square"], args["width-marker"], aruco_dict)
    board_img = cv.aruco_CharucoBoard.draw(
                board, (args["squares-x"] * 200, args["squares-y"] * 200), 10, 1)
        
    # Get path to data folder
    save_path = pathlib.Path(__file__).parent.resolve() / ".." / "data" / "charuco.png"

    # Save board
    if cv.imwrite(str(save_path), board_img) is True:
        print(f"Saved as charuco.png in cli_data/")
    else:
        print("Failed to create board")
            

    