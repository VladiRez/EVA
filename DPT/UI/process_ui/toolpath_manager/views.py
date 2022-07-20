from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.contrib import messages
from django import forms

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
        ui_module.transmit("eva_interface", Requests.STOP_BACKDRIVING)

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
    if confirmation is not None and confirmation != Requests.BACKDRIVING_MODE:
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

    # INIT
    ##############################################################################################

    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_WP, hash_id))
    errors = []
    joint_angles = None
    name = None
    creation_time = None
    name_form = None

    deleted = False

    # GET WAYPOINT INFO
    ###############################################################################################

    try:
        (sender, msg) = ui_module.receive(from_sender="op_data", timeout=100)

        if msg[1] == Responses.NONEXISTENT_WAYPOINT:
            ret_hash_id = msg[0]
            errors.append("No Waypoint with given ID.")
        else:
            (ret_hash_id, name, joint_angles, creation_time) = msg

        # If wrong waypoint is returned
        if ret_hash_id != hash_id:
            errors.append("Wrong Waypoint received from Database")

    except ReceiveTimeoutException:
        errors.append("Timeout: No Response from Database")


    # DELETE WAYPOINT
    ##############################################################################################

    if request.method == "POST":
        if "delete" in request.POST:
            try:
                ui_module.transmit("op_data", (Requests.DEL_WP, hash_id))
                (sender, msg) = ui_module.receive(from_sender="op_data",
                        expected_msg=(Requests.DEL_WP, Responses.NONEXISTENT_WAYPOINT), timeout=100)

                if msg == Requests.DEL_WP:
                    messages.info(request, "Waypoint successfully deleted.")
                    deleted = True
                else:
                    errors.append(request, "Could not delete waypoint.")

            except ReceiveTimeoutException:
                errors.append("Timeout: No Response from Database")

        elif "change_name" in request.POST:
            name_form = ChangeNameForm(request.POST)
            if not name_form.is_valid():
                errors.append("Invalid Name.")

            else:
                new_name = name_form.cleaned_data["new_name"]
                name = new_name
                ui_module.transmit("op_data", (Requests.CHANGE_WP_NAME, hash_id, new_name))
                try:
                    (sender, msg) = ui_module.receive(from_sender="op_data",
                                                      expected_msg=(Requests.CHANGE_WP_NAME,),
                                                      timeout=100)

                    if msg == Responses.UNEXPECTED_FAILURE:
                        errors.append("Unexpected Failure in Database")

                    else:
                        messages.info(request, "Name changed successfully!")

                except ReceiveTimeoutException:
                    errors.append("Timeout: No Response from Database")




    # CONTEXT AND RETURN
    ###############################################################################################

    if name is not None:
        name_form = ChangeNameForm({"new_name": name})
    elif name_form is None:
        name_form = ChangeNameForm()

    if creation_time is not None:
        # Convert time float to readable format
        timestr = time.asctime(time.localtime(creation_time))
    else:
        timestr = None

    context = {"deleted": deleted, "hash_id": hash_id, "name": name, "joint_angles": joint_angles,
               "timestr": timestr, "name_form": name_form}

    return render(request, "toolpath_manager/waypoint_detail.html", context)


def create_toolpath(request):
    return HttpResponse("Not yet implemented")


class ChangeNameForm(forms.Form):
    new_name = forms.CharField(label="Name ändern: ", max_length=80)

