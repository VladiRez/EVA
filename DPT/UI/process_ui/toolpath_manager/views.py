from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.contrib import messages

import time

from dpt_module import DptModule, Requests, Responses, ReceiveTimeoutException

ui_module = DptModule("ui")

def index(request, reset=False):
    """
    Main Landing Page for the EVA UI
    """

    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_ALL_WP_IDS,))
    errors = []
    wp_tuple = None

    try:
        (sender, (ids, names)) = ui_module.receive(from_sender="op_data", timeout=100)
        wp_tuple = zip(ids, names)
    except ReceiveTimeoutException:
        errors.append("Timeout: No response from Database")

    if reset:
        print("Test")
        ui_module.transmit("eva_interface", (Requests.STOP_BACKDRIVING,))

        try:
            (sender, conf) = ui_module.receive(from_sender="eva_interface",
                                 expected_msg=(Requests.STOP_BACKDRIVING,), timeout=10000)
            if conf == Requests.STOP_BACKDRIVING:
                messages.info(request, "Successfully unlocked EVA.")
        except ReceiveTimeoutException:
            errors.append("Failed to unlock EVA.")


    context = {"wps": wp_tuple, "errors": errors}
    return render(request, "toolpath_manager/index.html", context=context)

def backdriving(request):
    """
    Enable EVA backdriving mode, where the head can be moved and waypoints can be saved to
    the databse.
    """

    ui_module.flush_queue()
    ui_module.transmit("eva_interface", (Requests.BACKDRIVING_MODE,))
    errors = []
    confirmation = None
    try:
        (sender, confirmation) = ui_module.receive(from_sender="eva_interface", timeout=10000)

    except ReceiveTimeoutException:
        errors.append("Timeout: No Response from EVA_INTERFACE")

    # What if an unexpected response is received
    if confirmation != Requests.BACKDRIVING_MODE:
        if confirmation == Responses.LOCK_FAILED:
            errors.append("Eva Lock failed. See if EVA is connected and no other lock exists.")
        else:
            errors.append("Messaging Error: Wrong message received.")


    context = {"confirmation": confirmation, "errors": errors}

    return render(request, "toolpath_manager/backdriving.html", context=context)


def waypoint_detail(request, hash_id, delete=False):
    """
    Detailed information regarding the selected waypoint.
    """

    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_WP, hash_id))
    errors = []
    joint_angles = None
    name = None
    creation_time = None
    try:
        (sender, msg) = ui_module.receive(from_sender="op_data", timeout=100)
        (ret_hash_id, name, joint_angles, creation_time) = msg

        # If wrong waypoint is returned
        if ret_hash_id != hash_id:
            errors.append("Wrong Waypoint received from Database")

    except ReceiveTimeoutException:
        errors.append("Timeout: No Response from Database")

    if delete:
        try:
            ui_module.transmit("op_data", (Requests.DEL_WP, hash_id))
            (sender, msg) = ui_module.receive(from_sender="op_data",
                    expected_msg=(Requests.DEL_WP, Responses.NONEXISTENT_WAYPOINT), timeout=100)

            if msg == Requests.DEL_WP:
                messages.info(request, "Waypoint successfully deleted.")
            else:
                messages.info(request, "Could not delete waypoint.")

        except ReceiveTimeoutException:
            errors.append("Timeout: No Response from Database")

    if creation_time is not None:
        # Convert time float to readable format
        timestr = time.asctime(time.localtime(creation_time))
    else:
        timestr = None

    context = {"hash_id": hash_id, "name": name, "joint_angles": joint_angles, "timestr": timestr}

    return render(request, "toolpath_manager/waypoint_detail.html", context)

def create_toolpath(request):
    return HttpResponse("Not yet implemented")