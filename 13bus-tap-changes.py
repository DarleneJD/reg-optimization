"""
Run power flow on the file "IEEE13_v1.dss" with the regulator ACTIVE and without PV.
Export the voltage profile (plot profile) and the event log.
Then, gradually add each PV lateral and repeat the process.
At the end, compare the results.

It is important to always check which buses (if any) are violating voltage limits.
"""

import py_dss_interface
import numpy as np
import matplotlib.pyplot as plt

import py_dss_interface
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# FILE CONFIGURATION
# ============================================================
dss_file = r"D:\Users\EdioD\PycharmProjects\variacao-tensao-frp\13Bus\23742222\IEEE13_v1.dss"


dss = py_dss_interface.DSS()
dss.text(f"compile [{dss_file}]")

# Energy meter at the feeder head
dss.text("New Energymeter.EM1 element=line.650632 terminal=1")

# Voltage bases
dss.text("set voltagebases=[115, 4.16, .48]")
dss.text("calcvoltagebases")

# Daily simulation mode
dss.text("set mode=daily number=2880")
dss.text("Solve")

# Export event log
dss.text("Export Eventlog")

# dss.text("Show taps")
# dss.text("Export Meters")

# Voltage limits
dss.text("Set normvminpu=0.90")
dss.text("Set normvmaxpu=1.03")

# dss.text("Plot profile")
# dss.text("Show V LN Nodes ")
# dss.text("Export Losses")

# Uncomment to print per-bus voltages
# for bus in dss.circuit.buses_names:
#     dss.circuit.set_active_bus(bus)
#     print(bus)
#     print(dss.bus.vmag_angle_pu)  # V_LN voltage equivalent to "Show LN Nodes"
