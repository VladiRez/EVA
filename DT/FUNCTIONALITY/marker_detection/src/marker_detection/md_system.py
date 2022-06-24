"""The main module for the Zed2 camera marker detection system.

Part of the project AI-in-Orbit, Fachbereich Datenverarbeitung in der Konstruktion,
Technische Universität Darmstadt, Germany, 2021
Author: Robert Knobloch, TU Darmstadt, robert.knobloch@stud.tu-darmstadt.de
"""

import json
import pathlib
import numpy as np
import cv2
import pyzed.sl as sl


class MarkerDetectionSystem:
    """This class uses a Zed2 Camera and the OpenCV Aruco Marker System to
    detect and locate AruCo markers in 3D Space.

    The coordinate system is set by a charuco marker board, which allows 
    reliable positioning of the detected markers in the real space. 
    Initialization requires a camera calibration file for the zed2 camera
    as well as a json config file for setting parameters related to the 
    charuco and aruco markers and the coordinate system. 

    Attributes
    ----------
    highest_marker_id : int
            Highest possible marker ID for detection, choose as low as possible
    video_output : bool
        Set True to get an opencv output window displaying the detected markers
    zed2_config_file : Path
        Path to the zed2 camera configuration file containing the camera calibration
    settings_file : Path
        Path to the json file containing the marker detection settings.
    zed : pyzed.sl.Camera
        The main interface of the Zed2 API
    current_img_zed : pyzed.sl.Mat
        Matrix that stores the current camera image    
    depth_map : pyzed.sl.Mat
        Matrix that stores the current depth image    
    point_cloud : pyzed.sl.Mat
        Stores the 3D point cloud of the camera image
    marker_pixel_coordinates : numpy.ndarray 
        Pixel coordinates of the detected markers in the video feed. 
        Shape is (highest_marker_id, 2), they are stored in a 2D matrix, 
        each row belongs to its corresponding marker (marker id == row index).
    marker_coordinates : numpy.ndarray
        Actual 3D coordinates of the centers of the detected markers.
        Shape is (highest_marker_id, 3), they are stored in a 2D matrix, 
        each row belongs to its corresponding marker (marker id == row index).      
    cameraMatrix : numpy.ndarray
        3x3 matrix, the camera matrix of the camera in use
    distCoeff: numpy.ndarray
        Vector of distorion coefficients        
    runtime_params : pyzed.sl.RuntimeParamters
        Object that stores the zed camera runtime parameters     

    aurco_parameters : cv2.aruco.DetectorParameters
        Object that stores the paramters used in the cv2 marker detection
    aurco_dictionary : cv2.aruco.Dictionary
        Determines the set of markers used in the detection process, a list of dictionaries
        can be found here: https://docs.opencv.org/4.5.3/d9/d6a/group__aruco.html
    chaurco_dictionary : cv2.aruco.Dictionary
        Aruco dictionary used in the charuco board
    charuco_board : cv2.aruco.CharucoBoard
        Object containing info about the charuco board
    coor_offset : numpy.ndarray
        Three dimensional transform array describing the vector from the charuco board
        coordinate system origin to the desired origin of the coordinate system (1x3)

    found_charuco : bool
        True if a charuco board could be found
    origin_trans : numpy.ndarray
        1x3 vector storing the coordinates of the charuco board origin in the 
        coordinate system of the camera (in m)       
    origin_rot : numpy.ndarray
        1x3 vector storing a simplified opencv Rodrigues rotation vector, describing the 
        rotation of the charuco board coordinate system relative to the camera coordinate
        system
    rot_matrix : numpy.ndarray
        3x3 matrix that is used to convert coordinates from the camera coordinate system
        to the charuco board coordinate system

    """

    def __init__(self, video_ouput, zed2_config_file, settings_file):
        """ Initializing the attributes and opening the camera

        Parameters
        ----------
        video_output : bool
            Set True to get an opencv output window displaying the detected markers
        zed2_config_file : Path
            Path to the zed2 camera configuration file containing the camera calibration
            Most often found in C:/ProgramData/StereoLabs/settings/
        settings_file : Path
            Path to the json file containing the marker detection settings.
        """

        self.video_output = video_ouput

        # ZED CAMERA/SDK INITIALIZATION (see class documentation for attribute details)
        ##########################################################################################

        self.zed = sl.Camera()
        self.current_img_zed = sl.Mat()
        self.depth_map = sl.Mat()
        self.point_cloud = sl.Mat()

        # Zed SDK initialization parameters
        # https://www.stereolabs.com/docs/api/structsl_1_1InitParameters.html
        init_params = sl.InitParameters()
        init_params.camera_fps = 0
        init_params.depth_mode = sl.DEPTH_MODE.QUALITY
        init_params.coordinate_units = sl.UNIT.CENTIMETER
        init_params.depth_stabilization = False
        init_params.depth_minimum_distance = 20
        init_params.depth_maximum_distance = 200

        resolution = "HD1080"
        res_dict = {"HD2K": sl.RESOLUTION.HD2K, "HD1080": sl.RESOLUTION.HD1080,
                    "HD720": sl.RESOLUTION.HD720, "VGA": sl.RESOLUTION.VGA}
        init_params.camera_resolution = res_dict[resolution]

        # Camera calibration (from Camera config file in C:/ProgramData/StereoLabs/settings/)
        # CHANGES WITH RESOLUTION AND CAMERA SERIAL NUMBER!
        # Download calibration for ZED camera with the right serial number from Stereolabs
        # and put it in ../data
        with open(zed2_config_file, 'r') as conf:
            # a dictionary the saves the extracted config parameters
            calib = {}
            # will be set to true once the correct paragraph has been found in the config file
            read = False
            # dictionary for finding the correct paragraph in the config file
            config_res_dict = {"HD2K": "[LEFT_CAM_2K]", "HD1080": "[LEFT_CAM_FHD]",
                               "HD720": "[LEFT_CAM_HD]", "VGA": "[LEFT_CAM_VGA]"}
            for line in conf:
                # Strip spaces and newlines from beginning and end
                line = line.strip()
                if read:
                    if(line == ""):
                        break
                    (key, val) = line.split("=")
                    calib[key] = float(val)

                # Start reading when relevant paragraph is reached
                if(line == config_res_dict[resolution]):
                    read = True

        self.cameraMatrix = np.array([[calib["fx"], 0,           calib["cx"]],
                                      [0,           calib["fy"], calib["cy"]],
                                      [0,           0,           1]])
        self.distCoeff = np.array([[calib["k1"]], [calib["k2"]],
                                   [calib["p1"]], [calib["p2"]], [calib["k3"]]])

        # Camera runtime parameters
        self.runtime_params = sl.RuntimeParameters()
        self.runtime_params.sensing_mode = sl.SENSING_MODE.STANDARD
        self.runtime_params.enable_depth = True

        # ARUCO/CHARUCO INITIALIZATION
        ##########################################################################################

        # AruCo Parameters: https://docs.opencv.org/4.5.3/d5/dae/tutorial_aruco_detection.html
        self.aruco_parameters = cv2.aruco.DetectorParameters_create()
        self.aruco_parameters.minOtsuStdDev = 3.0
        self.aruco_parameters.polygonalApproxAccuracyRate = 0.05
        self.aruco_parameters.perspectiveRemoveIgnoredMarginPerCell = 0.3
        self.aruco_parameters.adaptiveThreshWinSizeMax = 53
        self.aruco_parameters.adaptiveThreshWinSizeMin = 3
        self.aruco_parameters.adaptiveThreshWinSizeStep = 10

        with open(settings_file, "r") as md_settings_f:
            md_settings = json.load(md_settings_f)

        if md_settings is None:
            raise Exception(
                "Error while loading marker detection settings file.")

        self.highest_marker_id = md_settings["aruco"]["highest_marker_id"]

        self.marker_pixel_coordinates = np.empty((self.highest_marker_id, 2))
        self.marker_coordinates = np.zeros((self.highest_marker_id, 3))

        # Get AruCo dictionary from settings file
        self.aruco_dictionary = cv2.aruco.getPredefinedDictionary(
            getattr(cv2.aruco, md_settings["aruco"]["dictionary"]))
        self.charuco_dictionary = cv2.aruco.getPredefinedDictionary(
            getattr(cv2.aruco, md_settings["charuco"]["dictionary"]))
        # Set up charuco board
        self.charuco_board = cv2.aruco.CharucoBoard_create(
            md_settings["charuco"]["n_squares_x"], md_settings["charuco"]["n_squares_y"],
            md_settings["charuco"]["width_square"], md_settings["charuco"]["width_marker"],
            self.charuco_dictionary)

        # Get coordinate system offset given in config
        self.coor_offset = [[md_settings["coordinate_system_offset"]["x"]],
                            [md_settings["coordinate_system_offset"]["y"]],
                            [md_settings["coordinate_system_offset"]["z"]]]

        # COORDINATE SYSTEM INITIALIZATION
        ##########################################################################################

        self.found_charuco = False
        self.origin_rot, self.origin_trans, self.rot_matrix = None, None, None

        # Open the camera
        err = self.zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print("ERROR: FAILED TO OPEN CAMERA")
            exit(1)

    def update(self) -> bool:
        """Gets and analyzes a new picture

        Returns:
            bool: True if video stream is closed by user 
        """

        # Return True if system is not yet calibrated with CharuCo board
        if self.found_charuco == False:
            return True

        # Grab current image
        if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
            # A new image is available, take left image and depth map
            self.zed.retrieve_image(self.current_img_zed, sl.VIEW.LEFT)
            self.zed.retrieve_measure(self.depth_map, sl.MEASURE.DEPTH)

            # Convert Zed Images to numpy (opencv compatible) Matrix
            current_img = self.current_img_zed.get_data()
            depth_map_np = self.depth_map.get_data()

            # Remove alpha channel, because it is incompatible with
            # the detectMarkers function
            current_img = np.delete(current_img, 3, 2)

            # marker_corners is a list with n element, where n is the number of detected markers,
            # each element is a numpy array of shape (1, 4, 2)
            # marker_ids is a numpy array/vector of shape ("number of detected markers", 1)
            (marker_corners, marker_ids, _) = cv2.aruco.detectMarkers(
                current_img, dictionary=self.aruco_dictionary,
                parameters=self.aruco_parameters, cameraMatrix=self.cameraMatrix,
                distCoeff=self.distCoeff)

            current_img = cv2.aruco.drawAxis(
                current_img, self.cameraMatrix, self.distCoeff,
                self.origin_rot, self.origin_trans, length=0.1)

            if self.video_output:
                # Make a separate output picture to lay over the detected markers
                cv2.aruco.drawDetectedMarkers(
                    current_img, marker_corners, marker_ids)

                # Show current image with markers in an opencv window
                cv2.imshow("Zed2 Stream", current_img)

            elif cv2.getWindowProperty('Zed2 Stream', cv2.WND_PROP_VISIBLE) == 1:
                # If video ouput is deactivated, but there are
                # still open windows, close them
                cv2.destroyAllWindows()

            # Process markers only if there are any
            if marker_ids is not None:
                # Get point cloud of the positions of the image pixels in space
                self.zed.retrieve_measure(
                    self.point_cloud, measure=sl.MEASURE.XYZ, type=sl.MEM.CPU)

                # Loop through detected marker corners
                for k, marker_corner in enumerate(marker_corners):
                    # Get marker id for current corner set
                    id = marker_ids[k, 0]

                    if id > self.highest_marker_id:
                        print("""A marker was recognized with an ID higher than the defined 
                              maximum: It will be disregarded""")
                        continue

                    self.marker_pixel_coordinates[id, :] = marker_corner[0][0]

                    # Read the positional value from the point cloud
                    # Returns a tuple, first element being the ERROR_CODE, second the 4D
                    # numpy array, the last element of which is zero
                    pc_value = self.point_cloud.get_value(self.marker_pixel_coordinates[id, 0],
                                                          self.marker_pixel_coordinates[id, 1],
                                                          memory_type=sl.MEM.CPU)

                    # Check if pc_value contains valid values
                    if pc_value[0] is sl.ERROR_CODE.SUCCESS:

                        # Assign to corresponding board coordinate vector if not NaN
                        if not np.any(np.isnan(pc_value[1])):

                            # Convert to CharuCo board coordinate system
                            # (*100 for conversion to cm)
                            diff = np.reshape(
                                pc_value[1][0:3], (3, 1)) - (self.origin_trans * 100)
                            coor = np.matmul(self.rot_matrix, diff)

                            # Transform to coordinate system given in the config file.
                            coor = coor - self.coor_offset

                            # Put value in coordinate list
                            self.marker_coordinates[id, :] = np.transpose(coor)
                    else:
                        print(
                            f"ERROR: FAILURE TO READ THE POINT CLOUD: {pc_value[0]}")

            # Abort video stream
            key = cv2.waitKey(1)
            if key == ord("q") or cv2.getWindowProperty('Zed2 Stream', cv2.WND_PROP_VISIBLE) == 0:
                cv2.destroyAllWindows()
                return True
            return False

    def calibration(self) -> bool:
        """Detect the charuco board used for defining the coordinate system.
        Modifies or rather sets self.origin_rot, self.origin_trans, self.rot_matrix
        and self.found_charuco

        Returns:
            bool: True if successful
        """

        if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
            # see update() for documentation, very similar code
            self.zed.retrieve_image(self.current_img_zed, sl.VIEW.LEFT)
            current_img = self.current_img_zed.get_data()
            current_img = np.delete(current_img, 3, 2)

            (marker_corners, marker_ids, _) = cv2.aruco.detectMarkers(
                current_img, dictionary=self.charuco_dictionary,
                parameters=self.aruco_parameters, cameraMatrix=self.cameraMatrix,
                distCoeff=self.distCoeff)

            if len(marker_corners) == 0:
                self.found_charuco = False
                return False

            # charuco_corners and charuco_ids is similar to marker_corners and marker_ids
            (_, charuco_corners, charuco_ids) = cv2.aruco.interpolateCornersCharuco(
                marker_corners, marker_ids, current_img, self.charuco_board,
                cameraMatrix=self.cameraMatrix, distCoeffs=self.distCoeff)

            (success, self.origin_rot, self.origin_trans) = cv2.aruco.estimatePoseCharucoBoard(
                charuco_corners, charuco_ids, self.charuco_board, self.cameraMatrix,
                self.distCoeff, None, None, useExtrinsicGuess=False)

            if (not success) or self.origin_trans is None or self.origin_rot is None:
                self.found_charuco = False
                return False

        else:
            return False

        # Get the inverse of the matrix corresponding to the cv2 rotation vector
        rot_matrix_inv, _ = cv2.Rodrigues(self.origin_rot)
        self.rot_matrix = np.linalg.inv(rot_matrix_inv)
        self.found_charuco = True
        return True

    def get_marker_coordinates(self):
        """Return detected marker coordinates

        Returns:
            numpy.ndarray: Array of shape (highest_marker_id, 3), each row contains the position of
                           the corresponding marker (row number = marker id)
        """
        return self.marker_coordinates

    def get_marker_coordinate(self, id: int):
        """Return detected marker coordinates of marker with given id

        Args:
            id (int): ID of the marker

        Returns:
            numpy.ndarray: Array of shape (1,3) containing the 3D coordinates of the marker
        """
        return self.marker_coordinates[id, :]

    def __del__(self):
        """Close the opencv window and the camera"""
        cv2.destroyAllWindows()
        self.zed.disable_positional_tracking()
        self.zed.close()
