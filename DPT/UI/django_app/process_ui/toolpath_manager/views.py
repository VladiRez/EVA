from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse
from django import forms


import time
import os
import asyncio
import logging

from base_module import BaseModule, TimeoutException

OP_DATA_ADDR = os.environ["OP_DATA_ADDR"]
EVA_INTERFACE_ADDR = os.environ["EVA_INTERFACE_ADDR"]
op_data_server_count = int(os.environ["OP_DATA_SERVER_COUNT"])
eva_interface_server_count = int(os.environ["EVA_INTERFACE_SERVER_COUNT"])

ui_module = BaseModule()
ui_module.register_connection(OP_DATA_ADDR, op_data_server_count)
ui_module.register_connection(EVA_INTERFACE_ADDR, eva_interface_server_count)


async def index(request):
    """ Main Landing Page for the EVA UI
    """

    try:
        req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("GET_ALL_WP_IDS",))
        (response, ids, names) = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=1000)

        wp_tuple = zip(ids, names)

        req_id = await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("STOP_BACKDRIVING",))
        msg = await ui_module.client_receive(EVA_INTERFACE_ADDR, req_id, timeout=10000)

        response = msg[0]

        if response == "STOP_BACKDRIVING":
            messages.info(request, "Successfully unlocked EVA.")
        elif response != "NOT_IN_BACKDRIVING_MODE":
            messages.info("Could not unlock EVA.")

    except (TimeoutException, ResponseException) as ex:
        return HttpResponse(ex)

    context = {"wps": wp_tuple}
    return render(request, "toolpath_manager/index.html", context=context)


async def backdriving(request):
    """ Enable EVA backdriving mode, where the head can be moved and 
    waypoints can be saved to the databse.
    """

    try:
        req_id = await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("BACKDRIVING_MODE",))
        msg = await ui_module.client_receive(EVA_INTERFACE_ADDR, req_id, timeout=10000)

        response = msg[0]
        if response == "LOCK_FAILED":
            raise ResponseException("""Eva Lock failed. 
                                       See if EVA is connected and no other lock exists.""")
        elif response != "BACKDRIVING_MODE":
            raise ResponseException("""Unknown Error""")

    except (TimeoutException, ResponseException) as ex:
        HttpResponse(ex)

    context = {}
    return render(request, "toolpath_manager/backdriving.html", context=context)


async def waypoint_detail(request, wp_id):
    """ Detailed information regarding the selected waypoint.
    """

    try:
        if "change_name" in request.POST:
            name_form = ChangeNameForm(request.POST)
            if not name_form.is_valid():
                raise InternalException("Invalid Name.")
            new_name = name_form.cleaned_data["new_name"]

            req_id = await ui_module.client_transmit(OP_DATA_ADDR,
                                                        ("CHANGE_WP_NAME", wp_id, new_name))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=500)

            response = msg[0]
            if response == "CHANGE_WP_NAME":
                messages.info(request, "Name changed successfully!")
            else:
                raise ResponseException(f"Could not rename waypoint: {response}")

        # Get Waypoint Info
        req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("GET_WP", wp_id))
        msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

        response = msg[0]
        if response == "NONEXISTENT_OBJECT":
            raise ResponseException(f"No Waypoint with given ID {wp_id}.")
        else:
            (response, wp_id, name, joint_angles, creation_time) = msg

        if "delete" in request.POST:
            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("DEL_WP", wp_id))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "DEL_WP":
                messages.info(request, "Waypoint successfully deleted.")
            else:
                raise ResponseException(f"Could not delete waypoint: {response}")
        elif "goto" in request.POST:
            req_id = await ui_module.client_transmit(EVA_INTERFACE_ADDR, ("GOTO_WP", joint_angles))
            msg = await ui_module.client_receive(EVA_INTERFACE_ADDR, req_id, timeout=10000)

            response = msg[0]
            if response == "GOTO_WP":
                messages.info(request, "Successfully moved to waypoint.")
            else:
                raise ResponseException("Error: Could not get EVA Lock")

    except (TimeoutException, ResponseException, InternalException) as ex:
        return HttpResponse(ex)

    name_form = ChangeNameForm({"new_name": name})
    timestr = time.asctime(time.localtime(creation_time))

    context = {"wp_id": wp_id, "name": name, "joint_angles": joint_angles, "timestr": timestr,
               "name_form": name_form}
    return render(request, "toolpath_manager/waypoint_detail.html", context)


async def toolpath_index(request):
    try:
        if "new_tp" in request.POST:
            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("NEW_TP",))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=5000)

            response = msg[0]
            if response == "NEW_TP":
                tp_id = msg[1]
                messages.info(request, f"Created New Waypoint with ID: {tp_id}")
            else:
                raise ResponseException("Could not create New Waypoint.")

        req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("GET_ALL_TP_IDS",))
        msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=1000)

        response = msg[0]
        if response == "GET_ALL_TP_IDS":
            (response, ids, names) = msg
            tp_tuple = zip(ids, names)
        else:
            raise ResponseException("Unknown Error")

    except (TimeoutException, ResponseException, InternalException) as ex:
        return HttpResponse(ex)

    context = {"tps": tp_tuple}
    return render(request, "toolpath_manager/toolpath_index.html", context=context)

async def toolpath_detail(request, tp_id="62f501fd498cc3cb66b88f89"):

    try:
        # Get list of waypoints in the toolpath
        req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("GET_TP", tp_id))
        msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=1000)

        response = msg[0]
        if response == "GET_TP":
            (response, tp_id, tp_name, tp_timeline) = msg
        else:
            raise ResponseException(f"Error when getting Toolpath from DB: {response}")

        # Get all waypoint ids and names from DB for the selection box
        req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("GET_ALL_WP_IDS",))
        msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=1000)

        response = msg[0]
        if response == "GET_ALL_WP_IDS":
            (response, wp_ids, names) = msg
            wp_tuple = tuple(zip(wp_ids, names))
            wp_dict = {wp_id: name for (wp_id, name) in wp_tuple}
        else:
            raise ResponseException("Unknown Error")

        if "change_name" in request.POST:
            name_form = ChangeNameForm(request.POST)
            if not name_form.is_valid():
                raise InternalException("Invalid Name.")

            new_name = name_form.cleaned_data["new_name"]
            req_id = await ui_module.client_transmit(OP_DATA_ADDR,
                                                     ("CHANGE_TP_NAME", tp_id, new_name))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=500)

            response = msg[0]
            if response == "CHANGE_TP_NAME":
                messages.info(request, "Name changed successfully!")
            else:
                raise ResponseException(f"Could not rename waypoint: {response}")

        elif "delete" in request.POST:
            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("DEL_TP", tp_id))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "DEL_TP":
                messages.info(request, "Toolpath successfully deleted.")
            else:
                raise ResponseException(f"Could not delete waypoint: {response}")

        elif "execute" in request.POST:
            # The timeline is a list with actions, i.e. waypoints, grips
            # Filter only the waypoints and remove duplicates:
            wp_ids = filter(lambda act: act not in ("GRIP", "UNGRIP"), tp_timeline)
            unique_wp_ids = tuple(set(wp_ids))

            # Each wp represented as just its joint angles.
            # The index of each wp is the waypoint_number.
            unique_wps = []
            wp_number_dict = {}  # Dictionary mapping a waypoint id to its waypoint_number

            # Get joint angles for unique wps
            for (wp_number, wp_id) in enumerate(unique_wp_ids):
                req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("GET_WP", wp_id))
                msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

                response = msg[0]
                if response == "GET_WP":
                    (response, wp_id, name, joint_angles, creation_time) = msg
                    unique_wps.append(joint_angles)
                    wp_number_dict[wp_id] = wp_number
                else:
                    raise ResponseException("Could not get waypoint information")

            timeline = []
            for action in tp_timeline:
                if action in ("GRIP", "UNGRIP"):
                    timeline.append(action)
                else:
                    wp_id = action
                    timeline.append(wp_number_dict[wp_id])

            req_id = await ui_module.client_transmit(EVA_INTERFACE_ADDR,
                                                     ("EXECUTE_TP", unique_wps, timeline))

        elif "add_wp_to_tp" in request.POST:
            wp_to_add = request.POST.get("choose_waypoint")

            req_id = await ui_module.client_transmit(OP_DATA_ADDR,
                                                     ("ADD_WP_TO_TP", tp_id, wp_to_add))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "ADD_WP_TO_TP":
                tp_timeline.append(wp_to_add)
                messages.info(request, "Waypoint successfully added.")
            else:
                raise ResponseException("Error adding WP to Toolpath")

        elif "add_grip_to_tp" in request.POST:
            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("ADD_GRIP_TO_TP", tp_id,))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "ADD_GRIP_TO_TP":
                tp_timeline.append("GRIP")
                messages.info(request, "Grip successfully added.")
            else:
                raise ResponseException("Error adding Grip to Toolpath")

        elif "add_ungrip_to_tp" in request.POST:
            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("ADD_UNGRIP_TO_TP", tp_id,))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "ADD_UNGRIP_TO_TP":
                tp_timeline.append("UNGRIP")
                messages.info(request, "Ungrip successfully added.")
            else:
                raise ResponseException("Error adding Ungrip to Toolpath")

        elif "move_element" in request.POST:
            move_from = int(request.POST.get("from_position")) - 1
            move_to = int(request.POST.get("to_position")) - 1

            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("TP_MOVE_ACTION_TO_POS",
                                                     tp_id, move_from, move_to))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "TP_MOVE_ACTION_TO_POS":
                element = tp_timeline.pop(move_from)
                tp_timeline.insert(move_to, element)
                messages.info(request, "Sucessfully moved element.")
            else:
                raise ResponseException("Could not move element.")

        elif "rm_from_tp" in request.POST:
            wp_index = int(request.POST.get("wp_index"))

            req_id = await ui_module.client_transmit(OP_DATA_ADDR, ("RM_FROM_TP", tp_id, wp_index))
            msg = await ui_module.client_receive(OP_DATA_ADDR, req_id, timeout=100)

            response = msg[0]
            if response == "RM_FROM_TP":
                tp_timeline.pop(wp_index)
                messages.info(request, "Waypoint successfully deleted.")
            else:
                raise ResponseException("Could not delete waypoint.")

    except (TimeoutException, ResponseException, InternalException) as ex:
        return HttpResponse(ex)

    # Order timeline in a readable list for UI
    displayed_timeline = []
    for ind, action in enumerate(tp_timeline):
        if action in ("GRIP", "UNGRIP"):
            displayed_timeline.append((ind, action))
        else:
            wp_id = action
            if wp_id not in wp_dict.keys():
                displayed_timeline.append((ind, "DELETED_WP"))
                continue
            displayed_timeline.append((ind, wp_id, wp_dict[wp_id]))

    # Init Forms
    choose_waypoint_form = ChooseWaypointForm(wp_tuple)
    move_element_choices = tuple((i, i) for i in range(1, len(tp_timeline)+1))
    move_element_form = MoveElementForm(choices=move_element_choices)
    name_form = ChangeNameForm({"new_name": tp_name})

    context = {"tp_id": tp_id, "tp_name": tp_name,
               "choose_waypoint_form": choose_waypoint_form, "name_form": name_form,
               "timeline": displayed_timeline, "move_element_form": move_element_form}
    return render(request, "toolpath_manager/toolpath_detail.html", context=context)


# FORMS
###################################################################################################

class ChangeNameForm(forms.Form):
    new_name = forms.CharField(label="Change Name: ", max_length=80)


class ChooseWaypointForm(forms.Form):
    def __init__(self, choices):
        super().__init__()
        self.fields["choose_waypoint"] = forms.ChoiceField(choices=choices)


class MoveElementForm(forms.Form):
    def __init__(self, choices):
        super().__init__()
        self.fields["from_position"] = forms.ChoiceField(choices=choices)

        self.fields["to_position"] = forms.ChoiceField(choices=choices)


# EXCEPTIONS
###################################################################################################

class InternalException(Exception):
    def __init__(self, explanation, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.explanation = explanation

    def __str__(self):
        return f"Internal UI Module Error: {self.explanation}"


class ResponseException(Exception):
    def __init__(self, explanation, *args, **kwargs):
        super().__init__(self, explanation, *args, **kwargs)
        self.explanation = explanation

    def __str__(self):
        return f"Received unfavorable response from another module: {self.explanation}"