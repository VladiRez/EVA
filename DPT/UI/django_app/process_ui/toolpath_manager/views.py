from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.contrib import messages
from django import forms

import time
import os

from dpt_module import DptModule, Requests, Responses, ReceiveTimeoutException

ui_module = DptModule("ui")

OP_DATA_ADDR = os.environ["OP_DATA_ADDR"]
EVA_INTERFACE_ADDR = os.environ["EVA_INTERFACE_ADDR"]

def index(request, reset=False):
    """
    Main Landing Page for the EVA UI
    """

    ui_module.flush_queue()
    ui_module.transmit(OP_DATA_ADDR, (Requests.GET_ALL_WP_IDS,))
    errors = []
    wp_tuple = None

    try:
        (sender, (ids, names)) = ui_module.receive(timeout=100)
        wp_tuple = zip(ids, names)
    except ReceiveTimeoutException:
        errors.append("Timeout: No response from Database")

    if reset:
        ui_module.transmit("eva_interface", Requests.STOP_BACKDRIVING)

        try:
            (sender, conf) = ui_module.receive(expected_msg=(Requests.STOP_BACKDRIVING,), 
                                               timeout=10000)
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
    ui_module.transmit(EVA_INTERFACE_ADDR, (Requests.BACKDRIVING_MODE,))
    errors = []
    confirmation = None
    try:
        (sender, confirmation) = ui_module.receive(timeout=10000)

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
    ui_module.transmit(OP_DATA_ADDR, (Requests.GET_WP, hash_id))
    errors = []
    joint_angles = None
    name = None
    creation_time = None
    name_form = None

    deleted = False

    # GET WAYPOINT INFO
    ###############################################################################################

    try:
        (sender, msg) = ui_module.receive(timeout=100)

        if msg[1] == Responses.NONEXISTENT_OBJECT:
            ret_hash_id = msg[0]
            errors.append("No Waypoint with given ID.")
        else:
            (ret_hash_id, name, joint_angles, creation_time) = msg

        # If wrong waypoint is returned
        if ret_hash_id != hash_id:
            errors.append("Wrong Waypoint received from Database")

    except ReceiveTimeoutException:
        errors.append("Timeout: No Response from Database")


    # PROCESS POSTS
    ##############################################################################################

    if request.method == "POST":
        if "delete" in request.POST:
            try:
                ui_module.transmit(OP_DATA_ADDR, (Requests.DEL_WP, hash_id))
                (sender, msg) = ui_module.receive(from_sender="op_data",
                        expected_msg=(Requests.DEL_WP, Responses.NONEXISTENT_OBJECT), timeout=100)

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
                ui_module.transmit(OP_DATA_ADDR, (Requests.CHANGE_WP_NAME, hash_id, new_name))
                try:
                    (sender, msg) = ui_module.receive(expected_msg=(Requests.CHANGE_WP_NAME,),
                                                      timeout=100)

                    if msg == Responses.UNEXPECTED_FAILURE:
                        errors.append("Unexpected Failure in Database")

                    else:
                        messages.info(request, "Name changed successfully!")

                except ReceiveTimeoutException:
                    errors.append("Timeout: No Response from Database")

        elif "goto" in request.POST:
            if joint_angles is not None:
                ui_module.transmit(EVA_INTERFACE_ADDR, (Requests.GOTO_WP, joint_angles))
                try:
                    (sender, msg) = ui_module.receive(
                                      expected_msg=(Requests.GOTO_WP, Responses.LOCK_FAILED),
                                      timeout=10000)

                    if msg == Requests.GOTO_WP:
                        messages.info(request, "Successfully moved to waypoint.")
                    else:
                        errors.append("Error: Could not get EVA Lock")

                except ReceiveTimeoutException:
                    errors.append("Timeout: No Response from Eva_Interface")
            else:
                errors.append("Error getting joint angles.")


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
               "timestr": timestr, "name_form": name_form, "errors": errors}

    return render(request, "toolpath_manager/waypoint_detail.html", context)


def create_toolpath(request):
    errors = []

    # Get all waypoint ids and names from DB for the selection box
    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_ALL_WP_IDS,))
    wp_tuple = None
    wp_dict = None
    try:
        (sender, (ids, names)) = ui_module.receive(from_sender="op_data", timeout=100)
        wp_tuple = tuple(zip(ids, names))
        wp_dict = {wp_id: name for (wp_id, name) in wp_tuple}
    except ReceiveTimeoutException:
        errors.append("Timeout: No response from Database")

    # Get list of waypoints in the toolpath
    ui_module.flush_queue()
    ui_module.transmit("op_data", (Requests.GET_TP, "62f501fd498cc3cb66b88f89"))
    wp_id_list = None
    try:
        (sender, (tp_id, wp_id_list)) = ui_module.receive(from_sender="op_data", timeout=100)
    except ReceiveTimeoutException:
        errors.append("Timeout: No response from Database")

    # PROCESS POSTS
    ##############################################################################################

    if request.method == "POST":
        if "execute" in request.POST:
            wp_list_markup = []
            for i, wp_id in enumerate(wp_id_list):
                ui_module.flush_queue()
                ui_module.transmit("op_data", (Requests.GET_WP, wp_id))
                try:
                    (sender, msg) = ui_module.receive(from_sender="op_data", timeout=100)
                    (hash_id, name, joint_angles, creation_time) = msg
                except ReceiveTimeoutException:
                    errors.append("Timeout: No response from Database")
                wp_list_markup.append({"label_id": i, "joints": joint_angles})
            try:
                ui_module.transmit("eva_interface", (Requests.EXECUTE_TP, wp_list_markup))
            except ReceiveTimeoutException:
                errors.append("Timeout: No response from EVA INTERFACE")
        elif "add_to_tp" in request.POST:
            #select_wp_form = SelectWaypointForm(request.POST)
            #if not select_wp_form.is_valid():
            #    errors.append("Invalid Selection.")
            #else:
            #wp_to_add = select_wp_form.data["select_wp"]
            wp_to_add = request.POST.get("select_wp")
            ui_module.flush_queue()
            ui_module.transmit("op_data", (Requests.ADD_TO_TP, "62f501fd498cc3cb66b88f89",
                                           wp_to_add))
            try:
                (sender, msg) = ui_module.receive(from_sender="op_data", timeout=100)
                if msg == Requests.ADD_TO_TP:
                    wp_id_list.append(wp_to_add)
                    messages.info(request, "Waypoint successfully added.")
                else:
                    errors.append("Error adding WP to Toolpath")
            except ReceiveTimeoutException:
                errors.append("Timeout: No response from Database")
        elif "delete" in request.POST:
            try:
                wp_index = int(request.POST.get("wp_index"))
                ui_module.transmit("op_data", (Requests.RM_FROM_TP, "62f501fd498cc3cb66b88f89", wp_index))
                (sender, msg) = ui_module.receive(from_sender="op_data",
                        expected_msg=(Requests.RM_FROM_TP, Responses.NONEXISTENT_OBJECT), timeout=100)

                if msg == Requests.RM_FROM_TP:
                    wp_id_list.pop(wp_index)
                    messages.info(request, "Waypoint successfully deleted.")
                else:
                    errors.append("Could not delete waypoint.")

            except ReceiveTimeoutException:
                errors.append("Timeout: No Response from Database")

    wp_list = ((wp_id, wp_dict[wp_id], i) for (i, wp_id) in enumerate(wp_id_list))
    select_wp_form = SelectWaypointForm(tuple(wp_tuple))

    context = {"select_wp_form": select_wp_form, "wp_list": wp_list, "errors": errors}

    return render(request, "toolpath_manager/toolpath_editor.html", context=context)


class ChangeNameForm(forms.Form):
    new_name = forms.CharField(label="Name ändern: ", max_length=80)


class SelectWaypointForm(forms.Form):
    def __init__(self, choices):
        super().__init__()
        self.fields["select_wp"] = forms.ChoiceField(choices=choices)
