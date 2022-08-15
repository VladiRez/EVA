from django.shortcuts import render
from django.contrib import messages
from django import forms

import time
import os
import asyncio
import logging

from base_module import BaseModule, TimeoutException

OP_DATA_ADDR = os.environ["OP_DATA_ADDR"]
EVA_INTERFACE_ADDR = os.environ["EVA_INTERFACE_ADDR"]

ui_module = BaseModule()
ui_module.register_connection(OP_DATA_ADDR)
ui_module.register_connection(EVA_INTERFACE_ADDR)

async def index(request, reset=False):
    """ Main Landing Page for the EVA UI
    """

    await ui_module.client_transmit(OP_DATA_ADDR, ("GET_ALL_WP_IDS",))
    errors = []
    wp_tuple = None

    try:
        (response, ids, names) = await ui_module.client_receive(OP_DATA_ADDR, timeout=1000)
        wp_tuple = zip(ids, names)
    except TimeoutException:
        errors.append("Timeout: No response from Database")

    if reset:
        await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("STOP_BACKDRIVING",))

        try:
            (response,) = await ui_module.client_receive(EVA_INTERFACE_ADDR, timeout=10000)
            if response == "STOP_BACKDRIVING":
                messages.info(request, "Successfully unlocked EVA.")
        except TimeoutException:
            errors.append("Failed to unlock EVA.")


    context = {"wps": wp_tuple, "errors": errors}
    return render(request, "toolpath_manager/index.html", context=context)


async def backdriving(request):
    """ Enable EVA backdriving mode, where the head can be moved and 
    waypoints can be saved to the databse.
    """

    await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("BACKDRIVING_MODE",))
    errors = []
    response = None

    try:
        (response,) = await ui_module.client_receive(EVA_INTERFACE_ADDR, timeout=10000)
    except TimeoutException:
        errors.append("Timeout: No Response from EVA_INTERFACE")

    # What if an unexpected response is received
    if response == "LOCK_FAILED":
        errors.append("Eva Lock failed. See if EVA is connected and no other lock exists.")
    if response != "BACKDRIVING_MODE":
        errors.append("Unknown Error")

    context = {"errors": errors}

    return render(request, "toolpath_manager/backdriving.html", context=context)


async def waypoint_detail(request, wp_id, delete=False):
    """ Detailed information regarding the selected waypoint.
    """

    # INIT
    ##############################################################################################

    await ui_module.client_transmit(OP_DATA_ADDR, ("GET_WP", wp_id))
    errors = []
    joint_angles = None
    name = None
    creation_time = None
    name_form = None

    deleted = False

    # GET WAYPOINT INFO
    ###############################################################################################

    try:
        msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=100)
        response = msg[0]
        if response == "NONEXISTENT_OBJECT":
            errors.append(f"No Waypoint with given ID {msg[1]}.")
        else:
            (response, wp_id, name, joint_angles, creation_time) = msg

    except TimeoutException:
        errors.append("Timeout: No Response from Database")


    # PROCESS POSTS
    ##############################################################################################

    if request.method == "POST":
        if "delete" in request.POST:
            try:
                await ui_module.client_transmit(OP_DATA_ADDR, ("DEL_WP", wp_id))
                msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=100)

                response = msg[0]
                if response == "DEL_WP":
                    messages.info(request, "Waypoint successfully deleted.")
                    deleted = True
                else:
                    errors.append(request, f"Could not delete waypoint: {response}")

            except TimeoutException:
                errors.append("Timeout: No Response from Database")

        elif "change_name" in request.POST:
            name_form = ChangeNameForm(request.POST)
            if not name_form.is_valid():
                errors.append("Invalid Name.")

            else:
                new_name = name_form.cleaned_data["new_name"]
                name = new_name
                await ui_module.client_transmit(OP_DATA_ADDR, ("CHANGE_WP_NAME", wp_id, new_name))
                try:
                    msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=100)

                    response = msg[0]
                    if msg == "CHANGE_WP_NAME":
                        messages.info(request, "Name changed successfully!")
                    else:
                        errors.append(f"Could not rename waypoint: {response}")

                except TimeoutException:
                    errors.append("Timeout: No Response from Database")

        elif "goto" in request.POST:
            if joint_angles is not None:
                await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("GOTO_WP", joint_angles))
                try:
                    msg = await ui_module.client_receive(EVA_INTERFACE_ADDR, timeout=10000)

                    response = msg[0]
                    if response == "GOTO_WP":
                        messages.info(request, "Successfully moved to waypoint.")
                    else:
                        errors.append("Error: Could not get EVA Lock")

                except TimeoutException:
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

    context = {"deleted": deleted, "wp_id": wp_id, "name": name, "joint_angles": joint_angles,
               "timestr": timestr, "name_form": name_form, "errors": errors}

    return render(request, "toolpath_manager/waypoint_detail.html", context)


async def create_toolpath(request):
    errors = []

    # Get all waypoint ids and names from DB for the selection box
    await ui_module.client_transmit(OP_DATA_ADDR, ("GET_ALL_WP_IDS",))
    wp_tuple = None
    wp_dict = None
    try:
        msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=1000)
        (response, ids, names) = msg
        wp_tuple = tuple(zip(ids, names))
        wp_dict = {wp_id: name for (wp_id, name) in wp_tuple}
    except TimeoutException:
        errors.append("Timeout: No response from Database")

    # Get list of waypoints in the toolpath
    await ui_module.client_transmit(OP_DATA_ADDR, ("GET_TP", "62f501fd498cc3cb66b88f89"))
    tp_timeline = None
    try:
        msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=1000)
        response = msg[0]
        if response == "GET_TP":
            (response, tp_id, tp_timeline) = msg
        else:
            errors.append(f"Error when getting Toolpath from DB: {response}")
    except TimeoutException:
        errors.append("Timeout: No response from Database")

    # PROCESS POSTS
    ##############################################################################################

    if request.method == "POST":
        if "execute" in request.POST:
            wp_list_markup = []
            for i, wp_id in enumerate(tp_timeline):
                await ui_module.client_transmit(OP_DATA_ADDR, ("GET_WP", wp_id))
                try:
                    msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=100)
                    (response, wp_id, name, joint_angles, creation_time) = msg
                except TimeoutException:
                    errors.append("Timeout: No response from Database")
                wp_list_markup.append({"label_id": i, "joints": joint_angles})
            try:
                await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("EXECUTE_TP", wp_list_markup))
            except TimeoutException:
                errors.append("Timeout: No response from EVA INTERFACE")
        elif "add_to_tp" in request.POST:
            #select_wp_form = SelectWaypointForm(request.POST)
            #if not select_wp_form.is_valid():
            #    errors.append("Invalid Selection.")
            #else:
            #wp_to_add = select_wp_form.data["select_wp"]
            wp_to_add = request.POST.get("select_wp")
            await ui_module.client_transmit(OP_DATA_ADDR, ("ADD_TO_TP", "62f501fd498cc3cb66b88f89",
                                           wp_to_add))
            try:
                msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=100)
                response = msg[0]
                if response == "ADD_TO_TP":
                    tp_timeline.append(wp_to_add)
                    messages.info(request, "Waypoint successfully added.")
                else:
                    errors.append("Error adding WP to Toolpath")
            except TimeoutException:
                errors.append("Timeout: No response from Database")

        elif "delete" in request.POST:
            try:
                wp_index = int(request.POST.get("wp_index"))
                await ui_module.client_transmit(OP_DATA_ADDR, ("RM_FROM_TP", "62f501fd498cc3cb66b88f89", 
                                          wp_index))
                msg = await ui_module.client_receive(OP_DATA_ADDR, timeout=100)
                response = msg[0]
                if response == "RM_FROM_TP":
                    tp_timeline.pop(wp_index)
                    messages.info(request, "Waypoint successfully deleted.")
                else:
                    errors.append("Could not delete waypoint.")

            except TimeoutException:
                errors.append("Timeout: No Response from Database")

    
    if tp_timeline is None:
        tp_timeline_detailed = ()
    else:
        tp_timeline_detailed = ((wp_id, wp_dict[wp_id], i) for (i, wp_id) in enumerate(tp_timeline))
    if wp_tuple is None:
        select_wp_form = SelectWaypointForm(choices=())
    else:
        select_wp_form = SelectWaypointForm(wp_tuple)

    context = {"select_wp_form": select_wp_form, "wp_list": tp_timeline_detailed, "errors": errors}

    return render(request, "toolpath_manager/toolpath_editor.html", context=context)


class ChangeNameForm(forms.Form):
    new_name = forms.CharField(label="Name ändern: ", max_length=80)


class SelectWaypointForm(forms.Form):
    def __init__(self, choices):
        super().__init__()
        self.fields["select_wp"] = forms.ChoiceField(choices=choices)
