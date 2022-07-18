from django.shortcuts import render
from django.http import HttpResponse, Http404

import asyncio

from dpt_module import DptModule, Requests, Responses, ReceiveTimeoutException

ui_module = DptModule("ui")

def index(request):
    """
    Main Landing Page for the EVA UI
    """

    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_ALL_WP_IDS,))
    errors = []
    ids = None
    try:
        (sender, ids) = ui_module.receive(from_sender="op_data", timeout=100)

    except ReceiveTimeoutException:
        errors.append("Timeout: No response from Database")

    context = {"wp_ids": ids, "errors": errors}
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

def waypoint_detail(request, wp_id):
    """
    Detailed information regarding the selected waypoint.
    """

    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_WP, wp_id))
    errors = []
    try:
        (sender, msg) = ui_module.receive(from_sender="op_data", timeout=100)
        id = msg[0]
        joint_angles = msg[1]

        # If wrong waypoint is returned
        if wp_id != id:
            errors.append("Wrong Waypoint received from Database")

    except ReceiveTimeoutException:
        errors.append("Timeout: No Response from Database")

    context = {"wp_id": wp_id, "joint_angles": joint_angles}

    return render(request, "toolpath_manager/waypoint_detail.html", context)

def create_toolpath(request):
    return HttpResponse("Not yet implemented")