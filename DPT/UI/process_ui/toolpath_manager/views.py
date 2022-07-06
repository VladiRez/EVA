from django.shortcuts import render

from dpt_module import DptModule, Requests, ReceiveTimeoutException

def index(request):
    ui_module = DptModule("ui")
    ui_module.transmit("op_data", (2, 0))
    try:
        (_, ids) = ui_module.receive(timeout=1000)
    except ReceiveTimeoutException:
        ids = ("ERROR CONNECTING TO DATABASE: TIMEOUT")
    context = {"wp_ids": ids}

    return render(request, "toolpath_manager/index.html", context=context)
