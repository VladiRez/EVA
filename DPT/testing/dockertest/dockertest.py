from dpt_module import DptModule, Requests
import time

module = DptModule("dockertest")

# Write New Waypoint to database
module.transmit("op_data", (Requests.NEW_WP, [1,2,3,4,5,6]))
module.transmit("eva_interface", "testing/")
time.sleep(5)