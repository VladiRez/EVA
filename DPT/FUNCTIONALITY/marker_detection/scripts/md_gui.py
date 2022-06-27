"""Part of the project AI-in-Orbit, Fachbereich Datenverarbeitung in der Konstruktion,
Technische Universität Darmstadt, Germany
Author: Robert Knobloch, TU Darmstadt
"""

from os import path
from typing import Dict
from threading import Thread
import pathlib
from timeit import default_timer
import tkinter as tk

from src.marker_detection.md_system import MarkerDetectionSystem


def main(args: Dict[str, object]):
    """Entry function for running the marker detection manually with GUI.

    Args:
        args (Dict[str, object]): Dictionary of parser arguments
    """
    gui = MarkerDetectionGUI()
    gui.start()


class MarkerDetectionGUI:
    """A class used to create and maintain the GUI for the marker detection test bench

    Tkinter runs in the main thread, while the MarkerDetectionSystem runs in another.

    ATTRIBUTES
    ----------
    root : tk.Tk
        The root element for the tkinter GUI
    mds : MarkerDetectionSystem
        The object used for the marker detection
    str_pos : str
        The string used to output the marker positions
    value_pos : tkinter.StringVar
        Object that stores the str_pos string for use in a widget
    updatetime : tkinter.StringVar
        Object that stores the time it takes to process a frame for use in a widget
    delta_time : float
        The time that passed while a frame is processed
    framerate : float
        The current framerate of the video
    str_thresh_min : tk.StringVar
        tkinter string variable for storing the adaptive thresholding minimum window size
    str_thresh_step : tk.StringVar
        tkinter string variable for storing the adaptive thresholding step, meaning the
        increase in the window size each thresholding step
    str_thresh_count : tk.StringVar
        tkinter string variable for storing how often the thresholding window size is increased
    abort : bool
        True if program should be aborted

    """

    def __init__(self, video_output=True):
        """Create tkinter window and initialize MarkerDetectionSystem

        Args:
            video_output (bool, optional): Show video output. Defaults to True.
        """
        # Create root window
        self.root = tk.Tk()
        self.root.title("Marker Detection")

        self.str_pos = ""
        self.updatetime = tk.StringVar()
        self.delta_time = None
        self.framerate = None
        self.value_pos = tk.StringVar()
        settings_file = pathlib.Path(__file__).parent.parent.resolve() \
            / "cli_data" / "md_settings.json"
        calibration_file = pathlib.Path(__file__).parent.parent.resolve() \
            / "cli_data" / "calibration.conf"
        self.mds = MarkerDetectionSystem(video_ouput=video_output,
                                         zed2_config_file=calibration_file, settings_file=settings_file)
        self.mds_thread = Thread(target=self.detection_loop)

        self.str_thresh_min = tk.StringVar()
        # Set entry field starting values to the ones defined in the MarkerDetectionSystem
        self.str_thresh_step = tk.StringVar()
        self.str_thresh_count = tk.StringVar()
        self.str_cell_margin = tk.StringVar()

        self.reset_entry_fields()

        self.abort = False

    def start(self):
        """Start the MarkerDetectionSystem thread, and the tkinter mainloop in the main thread"""
        self.mds_thread.start()

        # Label that displays update time
        label_time = tk.Label(self.root, textvariable=self.updatetime)
        label_time.grid(row=1, column=1, columnspan=2, padx=10)

        # Create label that displays marker positions
        label_pos = tk.Label(self.root, textvariable=self.value_pos)
        label_pos.grid(row=2, column=1, columnspan=2, padx=10)

        # Create label and entry field pairs
        label_thresh_min = tk.Label(
            self.root, text="Adaptive Thresholding Min")
        entry_thresh_min = tk.Entry(
            self.root, width=3, textvariable=self.str_thresh_min)
        label_thresh_min.grid(row=3, column=1, padx=10)
        entry_thresh_min.grid(row=3, column=2, padx=10)

        label_thresh_step = tk.Label(
            self.root, text="Adaptive Thresholding Step")
        entry_thresh_step = tk.Entry(
            self.root, width=3, textvariable=self.str_thresh_step)
        label_thresh_step.grid(row=4, column=1, padx=10)
        entry_thresh_step.grid(row=4, column=2, padx=10)

        label_thresh_count = tk.Label(
            self.root, text="Adaptive Thresholding Count")
        entry_thresh_count = tk.Entry(
            self.root, width=3, textvariable=self.str_thresh_count)
        label_thresh_count.grid(row=5, column=1, padx=10)
        entry_thresh_count.grid(row=5, column=2, padx=10)

        label_cell_margin = tk.Label(self.root, text="Ignored Cell Margin")
        entry_cell_margin = tk.Entry(
            self.root, width=3, textvariable=self.str_cell_margin)
        label_cell_margin.grid(row=6, column=1, padx=10)
        entry_cell_margin.grid(row=6, column=2, padx=10)

        button_apply_changes = tk.Button(self.root, text="Apply changes",
                                         command=self.update_params)
        button_apply_changes.grid(row=7, column=1, columnspan=2, padx=10)

        # Call update_gui, which then calls itself regularly
        self.root.after(25, func=self.update_gui)

        # Call on-closing function when closing the tkinter window
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.root.mainloop()

    def detection_loop(self):
        """An infinite loop that updates the MarkerDetectionSystem and updates the string
        storing the marker positions"""
        while True:
            if self.mds.found_charuco == False:
                success = self.mds.calibration()
                continue

            # Start timer measuring the update time / video framerate
            start_time = default_timer()
            # mds.update() returns True if program should be aborted
            video_closed = self.mds.update()

            # End timer and set string for gui label
            end_time = default_timer()
            self.delta_time = round(end_time - start_time, ndigits=3)
            if self.delta_time == 0:
                self.framerate = 0
            else:
                self.framerate = round(1 / self.delta_time, ndigits=1)

            if video_closed or self.abort:
                break

            # The string for storing the position is rebuilt from scratch each frame
            self.str_pos = ""

            for id in range(self.mds.highest_marker_id):
                # Get the coordinates of the marker belonging to the current id
                coor = self.mds.get_marker_coordinate(id)

                # Format the coordinates and build the string
                self.str_pos += f"ID: {id:0>4d} Position "
                self.str_pos += " ".join(["{:+08.2f}".format(x) for x in coor])
                self.str_pos += "\n"

    def update_gui(self):
        """Updates the label in the GUI, calls itself 20 times per second"""
        self.value_pos.set(self.str_pos)
        self.updatetime.set(
            f"Update time (s): {self.delta_time}; {self.framerate} fps")
        self.root.after(50, func=self.update_gui)

    def update_params(self):
        """Set the MarkerDetectionSystem parameters to the entered values
        """
        try:
            # Will throw ValueError in case of wrong entry
            thresh_min = int(self.str_thresh_min.get())
            thresh_step = int(self.str_thresh_step.get())
            thresh_count = int(self.str_thresh_count.get())
            cell_margin = float(self.str_cell_margin.get())

            # Assign new aurco parameters
            self.mds.aruco_parameters.adaptiveThreshWinSizeMin = thresh_min
            self.mds.aruco_parameters.adaptiveThreshWinSizeStep = thresh_step
            # Calculate new thresholding max window size
            thresh_max = thresh_min + thresh_step * thresh_count
            self.mds.aruco_parameters.adaptiveThreshWinSizeMax = thresh_max
            self.mds.aruco_parameters.perspectiveRemoveIgnoredMarginPerCell = cell_margin

        except ValueError:
            tk.messagebox.showwarning(
                title="Value Error", message="Please insert a valid value")
            self.reset_entry_fields()

    def reset_entry_fields(self):
        """Reset the entry fields to hold the values currently in use
        """
        self.str_thresh_min.set(
            str(self.mds.aruco_parameters.adaptiveThreshWinSizeMin))
        self.str_thresh_step.set(
            str(self.mds.aruco_parameters.adaptiveThreshWinSizeStep))
        # Calculate the threshold count with the max size, min size and step
        mds_thresh_count = int((self.mds.aruco_parameters.adaptiveThreshWinSizeMax
                                - self.mds.aruco_parameters.adaptiveThreshWinSizeMin)
                               / self.mds.aruco_parameters.adaptiveThreshWinSizeStep)
        self.str_thresh_count.set(str(mds_thresh_count))
        self.str_cell_margin.set(
            str(self.mds.aruco_parameters.perspectiveRemoveIgnoredMarginPerCell))

    def _on_closing(self):
        """Executed when closing the tkinter window"""
        # Exit MDS thread
        self.abort = True
        self.mds_thread.join()
        # Exit tkinter
        self.root.destroy()


if __name__ == "__main__":
    main()
