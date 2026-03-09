import numpy as np
from PyQt5.QtCore import pyqtSignal, QLocale, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QShortcut, QComboBox

from qt_mods import VarLine
from sys import platform


if platform == 'win32':
    default_folder = r"C:\PBM\Laser_Irradiance_measurements"
    # default_folder = "/Laser_irradiance_measurements"
else:
    # default_folder = r"/home/lightomics/pbm/experiment_files/laser_irradiance_meas" # tours
    default_folder = r"/home/pbm-precision/pbm/Laser_irradiance_measurement" # grenoble

def find_nearest_index(array, value):
    if value < array.min() or value > array.max():
        return None
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

class PowerCalc(QWidget):
    irradiance_emit = pyqtSignal(tuple)

    def __init__(self, distance=None, laser_power=None, laser_source=None):
        super().__init__()
        self.setLocale(QLocale('C'))
        self.setWindowTitle("Irradiance Calculation")

        self.laser_list = QComboBox()
        self.laser_list.addItems(["670 nm 2W (Tours)", "670 nm 5W (Grenoble)", "808 nm 2W (Tours)", "808 nm 5W (Grenoble)"])
        # self.laser_list.addItems(["670 nm 2W (Tours)", "808 nm 2W (Tours)"])
        # self.laser_list.addItems(["670 nm 5W (Grenoble)", "808 nm 5W (Grenoble)"])
        self.laser_list.currentTextChanged.connect(self.choose_laser_source)

        # distances = np.load(default_folder + '/13octobre_distances_lues.npy') # tours
        # powers = np.load(default_folder + '/13octobre_puissances_laser_x20mW.npy') # tours
        # self.data = np.load(default_folder + '/13octobre_interpolees.npy').transpose() # tours
        # self.distances = np.load(default_folder + '/20octobre_distances_lues.npy') # grenoble
        # self.powers = np.load(default_folder + '/20octobre_puissances_laser.npy') # grenoble
        # self.data = np.load(default_folder + '/20octobre_interpolees.npy').transpose() # grenoble
        # print(self.distances.shape, self.powers.dtype, self.data.shape)

        self.distance_read = VarLine('Distance (read)', callback=None, units={'cm':1}, decimals=1, wide=True, unit_width=50, right_align=False)
        self.distance_read.var.setRange(0,14.6)
        if distance is not None:
            self.distance_read.var.setValue(distance)
        else:
            self.distance_read.var.setValue(0.)

        self.laser_power = VarLine('Laser power', None, tracked=True, units={'W':1, 'x20 mW':1}, decimals=1, wide=True, unit_width=50, right_align=False)
        self.laser_power.var.setRange(0,5.1)
        if laser_power is not None:
            self.laser_power.var.setValue(laser_power)
        else:
            self.laser_power.var.setValue(20)

        self.irradiance = VarLine('Irradiance', None, tracked=True, units={'mW/cm²':1}, decimals=1, inform_only=True, wide=True, unit_width=50, right_align=False)
        self.distance_read.var.valueChanged.connect(self.update)
        self.laser_power.var.valueChanged.connect(self.update)

        try:
            self.laser_list.setCurrentText(laser_source)
        except:
            self.laser_list.setCurrentText("808 nm 5W (Grenoble)")
        self.choose_laser_source(self.laser_list.currentText())

        self.update()
        self.init_ui()

    def update(self, *args):
        dist_index = find_nearest_index(self.distances, self.distance_read.getValue())
        power_index = find_nearest_index(self.powers, self.laser_power.getValue())
        irradiance = self.data[dist_index, power_index]*1.025 # +2.5% to correct for the thickness of the adapter for the Pmeter probe.
        self.distance_read.setValue(self.distances[dist_index])
        self.laser_power.setValue(self.powers[power_index])
        self.irradiance.setValue(irradiance)

    def choose_laser_source(self, new_laser_source):
        # print(new_laser_source)
        match new_laser_source:
            case "670 nm 5W (Grenoble)":
                pass
            case "808 nm 5W (Grenoble)":
                self.distances = np.load(default_folder + '/20octobre_distances_lues.npy')  # grenoble 808
                self.powers = np.load(default_folder + '/20octobre_puissances_laser.npy')  # grenoble 808
                self.data = np.load(default_folder + '/20octobre_interpolees.npy').transpose()  # grenoble 808
                self.laser_power.change_units("W")
                self.laser_power.var.setDecimals(1)
            case "670 nm 2W (Tours)":
                pass
            case "808 nm 2W (Tours)":
                self.distances = np.load(default_folder + '/05decembre_distances_lues.npy') # tours 808
                self.powers = np.load(default_folder + '/05decembre_puissances_laser_x20mW.npy') # tours 808
                self.data = np.load(default_folder + '/05decembre_interpolees.npy').transpose() # tours 808
                self.laser_power.change_units("x20 mW")
                self.laser_power.var.setDecimals(0)
        self.laser_power.var.setRange(self.powers.min(), self.powers.max())
        self.distance_read.var.setRange(self.distances.min(), self.distances.max())
        self.update()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.laser_list)
        layout.addLayout(self.distance_read)
        layout.addLayout(self.laser_power)
        layout.addLayout(self.irradiance)

        self.shortcut_ok = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.shortcut_ok.activated.connect(self.ok)
        self.shortcut_ok2 = QShortcut(QKeySequence(Qt.Key_Enter), self)
        self.shortcut_ok2.activated.connect(self.ok)
        self.shortcut_cancel = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_cancel.activated.connect(self.cancel)

        close_btn = QPushButton('OK')
        close_btn.clicked.connect(self.ok)
        cancel_btn  =QPushButton('Cancel')
        cancel_btn.clicked.connect(self.cancel)

        btns_layout = QHBoxLayout()
        btns_layout.addWidget(cancel_btn)
        btns_layout.addWidget(close_btn)

        layout.addLayout(btns_layout)
        self.setLayout(layout)

    def ok(self):
        self.distance_read.var.clearFocus()
        self.laser_power.var.clearFocus()
        values = (self.distance_read.getValue(), self.laser_power.getValue(), self.irradiance.getValue())
        self.irradiance_emit.emit(values)
        self.close()

    def cancel(self):
        self.close()
