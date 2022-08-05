from dpt_module import DptModule, Requests
import time

module = DptModule("dockertest")

# Write New Waypoint to database
module.transmit("DPT_op-data-interface", (Requests.NEW_WP, [1,2,3,4,5,6]))
time.sleep(5)