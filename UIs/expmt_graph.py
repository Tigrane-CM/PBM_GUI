import time
from datetime import datetime
import numpy as np
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton
from pyqtgraph import PlotWidget, LinearRegionItem

from qt_mods import strfdelta

maxpoints_graph = 10000
time_units = {'sec': 1, 'min': 60, 'hrs': 3600}

class ExpmtGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.graph = PlotWidget(labels={'left': 'Irradiance (mW/cm²)', 'bottom': 'Temps (min)'})
        self.region = LinearRegionItem((0.,0.), movable=False)
        self.graph.addItem(self.region)
        self.time_label = QLabel()
        self.time_label.setText("no experiment started yet...")

        layout = QGridLayout()
        label=QLabel("Experiment Progress")
        label.setStyleSheet("QLabel {font: bold 8pt;}")
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addWidget(self.time_label, 0, 1, 1, 1, Qt.AlignRight)
        layout.addWidget(self.graph, 1, 0, 1, 2)
        self.setLayout(layout)
        self.data = np.zeros((2,1))
        self.timescale = 'min'

        font = QFont("Arial", 8)
        self.graph.getPlotItem().getAxis('bottom').label.setFont(font)
        self.graph.getAxis('bottom').setTickFont(font)
        self.graph.getPlotItem().getAxis('left').label.setFont(font)
        self.graph.getAxis('left').setTickFont(font)
        self.div = 1
        self.points_per_sec = 10.

    @pyqtSlot(dict)
    def update_data(self, params):
        on_duration = params['experiment config']['on duration']['value']*time_units[params['experiment config']['on duration']['unit']]
        total_duration = params['experiment config']['total duration']['value']*time_units[params['experiment config']['total duration']['unit']]
        print(total_duration)
        repetition_time= params['experiment config']['repetition time']['value']*time_units[params['experiment config']['repetition time']['unit']]
        num_reps = params['experiment config']['num. illums']
        # if num_reps == 0:
        #     num_reps = 1
        laser_power = params['experiment config']['Laser irradiance (mW/cm²)']

        # if num_reps > 0:
        #     total_duration = (on_duration + repetition_time * (num_reps- 1))
        # else:
        #     total_duration = (on_duration + repetition_time * (num_reps))
        # print(total_duration)

        if total_duration==0:
            total_duration=0.1
        x = np.arange(float(int(total_duration*self.points_per_sec)))
        y = np.where((x/self.points_per_sec)%repetition_time<on_duration, np.ones(x.shape)*laser_power, np.zeros(x.shape))

        if num_reps < 1:
            y*=0

        self.data = np.array((x,y))
        self.update_graph()

    def update_graph(self):
        self.region.setRegion((0,0))
        while self.data.shape[1] > maxpoints_graph:
            self.data = self.data[:,::2]
        min_or_h = False
        if self.data[0][-1] / self.points_per_sec > 90.:
            self.data[0] /= 60
            self.graph.getPlotItem().setLabel('bottom', 'Time (min)')
            self.timescale = 'min'
            min_or_h = True
        if self.data[0][-1]/self.points_per_sec > 90.:
            self.data[0]/=60
            self.graph.getPlotItem().setLabel('bottom', 'Time (h)')
            self.timescale = 'h'
        if not min_or_h:
            self.graph.getPlotItem().setLabel('bottom', 'Time (s)')
            self.timescale = 's'

        x = self.data[0]/self.points_per_sec
        y = self.data[1]
        x = np.append(np.append([-0.1, -0.01],x), [x[-1]+0.01, x[-1]+0.1])
        y = np.append(np.append([0,0], y), [0,0])
        self.graph.clearPlots()
        self.graph.plot(x, y) # , pen=mkPen('w', width=2))
        

    @pyqtSlot(float)
    def update_time_elapsed(self, time_elapsed):
        if self.timescale != 's':
            time_elapsed /= 60.
        if self.timescale == 'h':
            time_elapsed /= 60.
        self.region.setRegion((0,time_elapsed))

    @pyqtSlot(tuple)
    def experiment_started(self, times: tuple):
        start_time, end_time = times
        self.time_label.setText('started at '+ start_time.strftime("%H:%M:%S") + ' on '+start_time.strftime("%d/%m/%Y")
                                +', end at ' + end_time.strftime("%H:%M:%S") + ' on ' + end_time.strftime("%d/%m/%Y"))

    @pyqtSlot(tuple)
    def experiment_finished(self, times):
        time_end, status, duration = times
        if status == 'killed':
            self.time_label.setText("last experiment killed at " + time_end.strftime("%H:%M:%S") + " on " + time_end.strftime("%d/%m/%Y") + ", after " + strfdelta(duration, "%H h%M m%S s"))
        else:
            self.time_label.setText("last experiment finished at " + time_end.strftime("%H:%M:%S") + ' on ' + time_end.strftime("%d/%m/%Y") + ", after " + strfdelta(duration, "%H h%M m%S s"))


class LiveGraph(QWidget):
    divide_chrono = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.graph = PlotWidget(labels={'left': 'State', 'bottom': 'Time (min)'})
        vb = self.graph.getPlotItem().getViewBox()
        vb.setYRange(-0.05,1.05, padding=None,update=True)
        vb.setLimits(yMin=-0.05, yMax=1.05, minYRange=1.1, maxYRange=1.1)

        self.time_label = QLabel()
        start_time = datetime.now()
        self.time_label.setText('graph started at ' + start_time.strftime("%H:%M:%S") + ' on ' + start_time.strftime("%d/%m/%Y"))

        self.reset_btn = QPushButton('Reset graph', clicked = self.reset)
        self.reset_btn.setFixedWidth(80)

        layout = QGridLayout()
        label = QLabel('Live Progress')
        label.setStyleSheet("QLabel {font: bold 8pt;}")
        layout.addWidget(label, 0, 0, 1, 1)
        layout.addWidget(self.time_label, 0, 1, 1, 1)
        layout.addWidget(self.reset_btn, 0, 2, 1, 1)
        layout.addWidget(self.graph, 1, 0, 1, 3)

        self.setLayout(layout)
        self.timescale = 'min'

        self.timer_thread = ChronoThread()
        self.timer_thread.time_elapsed.connect(self.update_graph)
        self.divide_chrono.connect(self.timer_thread.divide)
        self.timer_thread.start()

        self.laser_state = 0.
        self.x = [0.]
        self.y = [0.]
        self.timescale = 's'
        
        font = QFont("Arial", 8)
        self.graph.getPlotItem().getAxis('bottom').label.setFont(font)
        self.graph.getAxis('bottom').setTickFont(font)
        self.graph.getPlotItem().getAxis('left').label.setFont(font)
        self.graph.getAxis('left').setTickFont(font)
        self.graph.getAxis('left').setTicks([[(0., 'OFF'), (1., 'ON')],[]])

    @pyqtSlot(bool)
    def update_laser_state(self, laser_on):
        if laser_on:
            self.laser_state = 1.
        else:
            self.laser_state = 0.

    @pyqtSlot(float)
    def update_graph(self, time_elapsed):
        self.x.append(time_elapsed)
        self.y.append(self.laser_state)
        while len(self.x) > maxpoints_graph:
            self.x = self.x[::2]
            self.y = self.y[::2]
            self.divide_chrono.emit(2)
            # print(self.x)
        x = np.array(self.x)
        y = np.array(self.y)
        self.timescale = 's'
        if x[-1]>90.:
            x/=60.
            self.timescale='min'
        if x[-1]>90.:
            x/=60.
            self.timescale='h'

        self.graph.plot(x,y, clear=True) # , pen=mkPen('w', width=2))

        self.graph.setLabel('bottom', 'Time ('+self.timescale+')')

    def reset(self):
        self.timer_thread.reset()
        self.x = []
        self.y = []
        self.graph.getPlotItem().clearPlots()
        self.graph.update()
        start_time = datetime.now()
        self.time_label.setText('graph started at ' + start_time.strftime("%H:%M:%S") + ' on ' + start_time.strftime("%d/%m/%Y"))
        self.graph.getAxis('left').setTicks([[(0., 'OFF'), (1., 'ON')],[]])

    def closeEvent(self):
        self.timer_thread.stop()


class ChronoThread(QThread):
    time_elapsed = pyqtSignal(float)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.thread_active = False
        self.time_base = 100

    @pyqtSlot()
    def run(self):
        self.thread_active = True
        self.time_start_global = time.time()
        while True:
            QTest.qWait(self.time_base)
            self.time_elapsed.emit(time.time() - self.time_start_global)
            if not self.thread_active:
                return self.stop()

    @pyqtSlot(int)
    def divide(self, factor):
        self.time_base = self.time_base*factor
        return

    def stop(self, emit=False):
        self.thread_active=False
        if emit:
            self.finished.emit()

    def reset(self):
        self.time_start_global = time.time()
        self.time_base = 100
