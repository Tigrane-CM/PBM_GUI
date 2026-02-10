import numpy as np
from PyQt5.QtCore import pyqtSignal, QLocale, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QShortcut

from qt_mods import VarLine
from sys import platform


if platform == 'win32':
    default_folder = r"C:\PBM\Laser_Irradiance_measurements"
else:
    # default_folder = r"/home/lightomics/pbm/experiment_files/laser_irradiance_meas" # tours
    default_folder = r"/home/pbm-precision/pbm/experiment_files/laser_irradiance_meas" # grenoble

def find_nearest_index(array, value):
    if value < array.min() or value > array.max():
        return None
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

class PowerCalc(QWidget):
    irradiance_emit = pyqtSignal(tuple)

    def __init__(self, distance=None, laser_power=None):
        super().__init__()
        self.setLocale(QLocale('C'))
        self.setWindowTitle("Irradiance Calculation")

        # distances = np.load(default_folder + '/13octobre_distances_lues.npy') # tours
        # powers = np.load(default_folder + '/13octobre_puissances_laser_x20mW.npy') # tours
        # self.data = np.load(default_folder + '/13octobre_interpolees.npy').transpose() # tours
        self.distances = np.load(default_folder + '/20octobre_distances_lues.npy') # grenoble
        self.powers = np.load(default_folder + '/20octobre_puissances_laser.npy') # grenoble
        self.data = np.load(default_folder + '/20octobre_interpolees.npy').transpose() # grenoble
        print(self.distances.shape, self.powers.dtype, self.data.shape)

        self.distance_read = VarLine('Distance (read)', callback=None, units={'cm':1}, decimals=1, wide=True, unit_width=50, right_align=False)
        self.distance_read.var.setRange(0,14.6)
        if distance is not None:
            self.distance_read.var.setValue(distance)
        else:
            self.distance_read.var.setValue(0.)

        self.laser_power = VarLine('Laser power', None, tracked=True, units={'W':1}, decimals=1, wide=True, unit_width=50, right_align=False)
        self.laser_power.var.setRange(0,5.1)
        if laser_power is not None:
            self.laser_power.var.setValue(laser_power)
        else:
            self.laser_power.var.setValue(20)

        self.irradiance = VarLine('Irradiance', None, tracked=True, units={'mW/cm²':1}, decimals=1, inform_only=True, wide=True, unit_width=50, right_align=False)
        self.distance_read.var.valueChanged.connect(self.update)
        self.laser_power.var.valueChanged.connect(self.update)

        self.update()
        self.init_ui()

    def update(self, *args):
        dist_index = find_nearest_index(self.distances, self.distance_read.getValue())
        power_index = find_nearest_index(self.powers, self.laser_power.getValue())
        irradiance = self.data[dist_index, power_index]*1.025
        self.distance_read.setValue(self.distances[dist_index])
        self.laser_power.setValue(self.powers[power_index])
        self.irradiance.setValue(irradiance)

    def init_ui(self):
        layout = QVBoxLayout()
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
        values = (self.distance_read.getValue(), self.laser_power.getValue(), self.irradiance.getValue())
        self.irradiance_emit.emit(values)
        self.close()

    def cancel(self):
        self.close()
