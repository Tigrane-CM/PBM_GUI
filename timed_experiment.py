import time, json
from datetime import datetime, timedelta

from PyQt5.Qt import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtCore import Qt, QLocale, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QPushButton, QGridLayout, QSpacerItem, QFrame, QSizePolicy, QFileDialog, QLabel, QDialog,
                               QDialogButtonBox, QVBoxLayout, QWidget)
from PyQt5.QtTest import QTest

from power_calc import PowerCalc
from qt_mods import VarLine, strfdelta
from sys import platform

# print(platform)
if platform == 'win32':
    default_folder = r"C:\PBM\experiment_files"
else:
    # default_folder = r"/home/lightomics/pbm/experiment_files" # tours
    default_folder = r"/home/pbm-precision/pbm/experiment_files" # grenoble

time_units = {'sec': 1, 'min': 60, 'hrs': 3600}


def extract_controls(parent_app, instr_list):
    return {'laser':parent_app.laser_controller}

def do_save(save_path, params):
    pass

def freeze(laser_control):
    laser_control.ui.toggle.setDisabled(True)
    return

def unfreeze(laser_control):
    laser_control.ui.toggle.setEnabled(True)
    return

class ExpControl(QWidget):
    kill_thread = pyqtSignal()

    def __init__(self, parent_app, instr_list, expmt_graph=None, emb_setup=None):
        self.parent_app = parent_app
        self.first_setup = True
        self.params = None
        self.ui_active = True
        self.instr_list = instr_list
        self.expmt_graph = expmt_graph
        self.work_thread = None
        super().__init__()

        if emb_setup is not None:
            self.expmt_setup_embedded  = emb_setup
            self.expmt_setup_embedded.params_changed.connect(self.change_params)
            self.expmt_setup_embedded.go_time.connect(self.start_experiment)

        if self.ui_active:
            self.btn_file_launch = QPushButton('Load\nfrom file', clicked=self.load_from_file)
            self.btn_setup = QPushButton('Start\nExperiment', clicked=self.expmt_setup_embedded.go)
            self.btn_kill = QPushButton('Kill\nExperiment', clicked = self.kill_expmt)

            self.btn_setup.setFixedHeight(50)
            self.btn_kill.setFixedHeight(50)
            self.btn_file_launch.setFixedHeight(50)
            self.btn_setup.setFixedWidth(110)
            self.btn_kill.setFixedWidth(110)
            self.btn_file_launch.setFixedWidth(60)

            self.state_label = QLabel()
            self.state_label.setText("Standby\n")
            self.state_label.setStyleSheet("QLabel {color: gray; font-size: 8pt}")

            self.grid = QGridLayout()
            control_frame = QFrame()
            control_box = QGridLayout()
            control_box.setSpacing(2)

            label = QLabel("Experiment Control")
            label.setStyleSheet("QLabel {font: bold 8pt;}")
            control_box.addWidget(label, 0, 0, 1, 1)
            control_box.addWidget(self.state_label, 1, 0, 1, 1, Qt.AlignCenter)
            control_box.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding), 0, 1, 2, 1)
            control_box.addWidget(self.btn_setup, 0, 2, 2, 2)
            control_box.addWidget(self.btn_kill, 0, 2, 2, 2)
            self.btn_kill.setDisabled(True)
            self.btn_kill.setHidden(True)
            control_box.addWidget(self.btn_file_launch, 0, 4, 2, 1)

            control_frame.setLayout(control_box)
            control_frame.setLineWidth(1)
            control_frame.setFrameStyle(0x0001)
            self.grid.addWidget(control_frame)
            self.setLayout(self.grid)

    @pyqtSlot()
    def start_experiment(self):
        you_sure = QDialog(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        QBtn = QDialogButtonBox.Yes | QDialogButtonBox.No
        you_sure.buttonBox = QDialogButtonBox(QBtn)
        you_sure.buttonBox.accepted.connect(lambda: self.launch_expmt(window=you_sure))
        you_sure.buttonBox.rejected.connect(you_sure.close)
        you_sure.layout = QVBoxLayout()
        you_sure.setWindowTitle("Start Experiment")
        message = QLabel("Do you want to start the experiment parametrized below ?")
        you_sure.layout.addWidget(message)
        you_sure.layout.addWidget(you_sure.buttonBox)
        you_sure.setLayout(you_sure.layout)
        you_sure.exec()

    def launch_expmt(self, window=None):
        if window is not None:
            window.close()
        self.expmt_setup_embedded.setDisabled(True)
        if not self.parent_app.win_unsleep_flag:
            self.parent_app.win_unsleep()
            self.reauthorize_win_sleep = True
        self.work_thread = ExpmtThread(self.parent_app, [], self.params, self.expmt_graph)
        self.work_thread.finished.connect(self.end_work)
        self.work_thread.start()
        if self.ui_active:
            self.btn_setup.setDisabled(True)
            self.btn_setup.setHidden(True)
            self.btn_kill.setEnabled(True)
            self.btn_kill.setVisible(True)
            self.btn_file_launch.setDisabled(True)
            self.state_label.setText("Running...\n")
            self.state_label.setStyleSheet("color: red")

    @pyqtSlot(dict)
    def change_params(self, params):
        self.params=params
        self.first_setup=False

    def load_from_file(self, param_file=None):
        if self.ui_active:
            param_file = QFileDialog.getOpenFileName(self, 'Select experiment parameter file',
                                                     directory=default_folder)[0]
        elif param_file is None:
            print('Give parameter file as kwarg "param_file"')
        print('Selected experiment file: '+ param_file)
        if param_file != '':
            with open(param_file, 'r') as f:
                self.params = json.load(f)
            f.close()
            print(self.params)
            # self.setup()
            self.expmt_setup_embedded.load_params(self.params)
        else:
            print('no file selected')

    def kill_expmt(self):
        you_sure = QDialog(None, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        QBtn = QDialogButtonBox.Yes | QDialogButtonBox.No
        you_sure.buttonBox = QDialogButtonBox(QBtn)
        you_sure.buttonBox.accepted.connect(lambda: self.stop_work(window=you_sure))
        you_sure.buttonBox.rejected.connect(you_sure.close)
        you_sure.layout = QVBoxLayout()
        you_sure.setWindowTitle("Kill Experiment")
        message = QLabel("Are you sure you want to kill this experiment ?")
        you_sure.layout.addWidget(message)
        you_sure.layout.addWidget(you_sure.buttonBox)
        you_sure.setLayout(you_sure.layout)
        you_sure.exec()

    def stop_work(self, window=None):
        if window is not None:
            window.close()
        if self.work_thread is not None:
            self.work_thread.thread_active=False
        self.expmt_setup_embedded.setDisabled(False)
        return

    @pyqtSlot()
    def end_work(self):
        self.expmt_setup_embedded.setDisabled(False)
        if self.work_thread is not None:
            self.work_thread.quit()
            self.work_thread.wait()
            del self.work_thread
            self.work_thread = None
        if self.ui_active:
            self.btn_kill.setDisabled(True)
            self.btn_kill.setHidden(True)
            self.btn_file_launch.setEnabled(True)
            self.btn_setup.setEnabled(True)
            self.btn_setup.setVisible(True)
            self.state_label.setText("Standby\n")
            self.state_label.setStyleSheet("color: gray")
        if self.reauthorize_win_sleep:
            self.parent_app.win_unsleep()
        return

    def closeEvent(self, e):
        if self.setup_window is not None:
            self.setup_window.close()

class ExpmtThread(QThread):
    finished = pyqtSignal(tuple)
    time_elapsed = pyqtSignal(float)
    started = pyqtSignal(tuple)

    def __init__(self, parent_app, instr_list, params, expmt_graph):
        super().__init__()
        self.controls = extract_controls(parent_app, instr_list)

        self.params = params
        self.extract_params()
        self.init_states = None

        self.thread_active=True
        self.setTerminationEnabled(True)
        self.time_elapsed.connect(expmt_graph.update_time_elapsed)
        self.started.connect(expmt_graph.experiment_started)
        self.finished.connect(expmt_graph.experiment_finished)

        self.time_start_print = None

    def extract_params(self):
        self.save_path = self.params["experiment config"]["folderpath"]
        self.save_path = self.save_path + '/' + time.strftime("%Y%m%d_%H%M%S")

        self.on_duration = self.params['experiment config']['on duration']['value']*time_units[ self.params['experiment config']['on duration']['unit']]/time_units['min']
        self.repetition_time = self.params['experiment config']['repetition time']['value']*time_units[ self.params['experiment config']['repetition time']['unit']]/time_units['min']
        self.num_reps = int(self.params['experiment config']['num. illums'])

        self.power = self.params['experiment config']['Laser irradiance (mW/cm²)']
        self.filename = self.params['experiment config']['filename']
        return

    @pyqtSlot()
    def run(self):
        print('PBM session starting')

        """ get initial states and prepare """
        self.init_states = self.get_initial_states()

        """ launch timer and run """


        minutes_between_two = self.repetition_time - self.on_duration
        duration_minutes = self.on_duration

        #save params
        do_save(self.save_path, self.params)

        total_duration = (self.on_duration + self.repetition_time * (self.num_reps - 1)) # in s

        time_start_global = time.time()
        self.time_start_print = datetime.now()
        start_status = "Experiment starting at " + self.time_start_print.strftime(
            "%H:%M:%S") + " on " + self.time_start_print.strftime("%d/%m/%Y")
        with open(self.filename, 'r') as f:
            params = json.load(f)
        if params.get('Start status') is None:
            with open(self.filename, "w") as f:
                params["Start status"] = start_status
                json.dump(params, f, indent=4)
        f.close()
        self.started.emit((self.time_start_print, self.time_start_print +  timedelta(minutes=total_duration)))
        time_next = time.time()  # + 2.
        freeze(self.controls['laser'])
        for i in range(self.num_reps):
            time_reached = False
            print(f'Waiting to launch illumination n. {i+1} of {self.num_reps} at '
                  + time.strftime("%Hh%Mm%Ss", time.localtime(time_next)))

            while not time_reached:
                QTest.qWait(10)
                print(time.strftime("%Hh%Mm%Ss"), end='\r')
                self.time_elapsed.emit(time.time()-time_start_global)
                if not self.thread_active:
                    return self.stop()
                if time.time() >= time_next:
                    time_reached = True
                    print('go!')

            self.do_one(i, time_start_global)
            time_next += (duration_minutes+minutes_between_two) * 60.
        unfreeze(self.controls['laser'])

        """ restore initial state """
        self.restore_initial_states()

        print('PBM session finished')
        time_end_print = datetime.now()
        total_duration = time_end_print - self.time_start_print
        self.finished.emit((time_end_print, 'finished', total_duration))
        end_status = "Experiment finished normally at " + time_end_print.strftime(
                "%H:%M:%S") + " on " + time_end_print.strftime(
                "%d/%m/%Y") + ", after " + strfdelta(total_duration, "%H h%M m%S s.")
        with open(self.filename, 'r') as f:
            params = json.load(f)
        if params.get('End status') is None:
            with open(self.filename, "w") as f:
                params["End status"] = end_status
                json.dump(params, f, indent=4)
        f.close()


    def stop(self):
        if self.controls['laser'].state:
            self.controls['laser'].off()
        unfreeze(self.controls['laser'])
        self.thread_active = False
        self.restore_initial_states()
        time_end_print = datetime.now()
        total_duration = time_end_print - self.time_start_print
        self.finished.emit((time_end_print, 'killed', total_duration))
        end_status = "Experiment killed at " + time_end_print.strftime(
                "%H:%M:%S") + " on " + time_end_print.strftime(
                "%d/%m/%Y") + ", after " + strfdelta(total_duration, "%H h%M m%S s.")
        with open(self.filename, 'r') as f:
            params = json.load(f)
        if params.get('End status') is None:
            with open(self.filename, "w") as f:
                params["End status"] = end_status
                json.dump(params, f, indent=4)
        f.close()

    def get_initial_states(self):
        if self.controls['laser'].state:
            self.controls['laser'].off()

    def restore_initial_states(self):
        self.controls['laser'].off()


    def do_one(self, idx, time_start_global):
        if not self.thread_active:
            return self.stop()
        print(f'running illumination n. {idx+1}')
        start_time = time.time()
        self.controls['laser'].on()
        time_elapsed = time.time() - start_time
        while time_elapsed < self.on_duration*60.:
            QTest.qWait(10)
            time_elapsed = time.time() - start_time
            self.time_elapsed.emit(time.time() - time_start_global)
            print(time.strftime("%Hh%Mm%Ss"), end='\r')
            if not self.thread_active:
                self.controls['laser'].off()
                print(f'stop button clicked, interrupting illumination after {time_elapsed:.0f} seconds elapsed.')
                return self.stop()
        self.controls['laser'].off()
        print(f'illumination n. {idx+1} ended')


# class ExpmtSetup_embedded(QWidget):
#     params_changed = pyqtSignal(dict)
#     params_for_graph = pyqtSignal(dict)
#     go_time = pyqtSignal()
#
#     def go(self):
#         params = self.save_params(file=True)
#         self.params_changed.emit(params)
#         self.params_for_graph.emit(params)
#         self.go_time.emit()
#
#     def cancel(self):
#         params = self.save_params(file=False)
#         self.params_changed.emit(params)
#         self.params_for_graph.emit(params)
#         self.close()
#
#     def __init__(self, parent_app, instr_list, params=None, first_setup=False, expmt_graph=None):
#         super().__init__()
#         self.parent_app = parent_app
#         controls = extract_controls(parent_app, instr_list)
#         if expmt_graph is not None:
#             self.params_for_graph.connect(expmt_graph.update_data)
#         self.first_setup=first_setup
#         try:
#             self.laser_control = controls['laser']
#         except:
#             print('missing laser controller')
#
#         self.setLocale(QLocale('C'))
#
#         """ timing parameters """
#         self.folderpath = default_folder
#         self.btn_select_dir = QPushButton('Select saving directory')
#         self.btn_select_dir.clicked.connect(self.select_dir)
#         self.btn_select_dir.setFixedWidth(80)
#
#         self.on_duration = VarLine("Duration of each illumination", None, display_decimals = 1, tracked=True, wide=True, right_align=False, units=time_units, name='on duration')
#         self.repetition_time = VarLine("Delay between illuminations", None, display_decimals = 1, tracked=True, wide=True, right_align=False, units=time_units, name='rep time')
#         self.num_reps = VarLine("Number of illuminations in session", None, decimals=0, tracked=True, wide=True, right_align=False, name='num reps')
#
#         self.on_duration.var.setRange(0., 1e18)
#         self.repetition_time.var.setRange(0., 1e18)
#         self.num_reps.var.setRange(0, 100000)
#         self.on_duration.var.valueChanged.connect(self.update_calc)
#         self.repetition_time.var.valueChanged.connect(self.update_calc)
#         self.num_reps.var.valueChanged.connect(self.update_calc)
#
#         self.distance_read = 0.
#         self.laser_power = 20
#
#         self.irradiance = VarLine("Irradiance", None, decimals = 1, tracked=True, wide=True, right_align=False, units={"mW/cm²":1}, unit_width=50, name='irradiance', inform_only=True)
#         self.irradiance.var.setRange(0, 100)
#         self.irradiance.var.valueChanged.connect(self.update_calc)
#         self.irradiance.setToolTip("Indicate laser irradiance here, from YOUR knowledge of it.\nUseful for logging experiments, but WILL NOT change the laser power by itself.")
#
#         self.irr_calc_btn = QPushButton('Compute')
#         self.irr_calc_btn.clicked.connect(self.irr_calc)
#
#         self.illum_duration = VarLine("Total duration of illumination", None, display_decimals = 1, wide=True, inform_only=True, right_align=False, units=time_units, name='illum duration')
#         self.total_duration = VarLine("Total duration of session", None, display_decimals = 1, wide=True, inform_only=True, right_align=False, units=time_units, name='tot duration')
#         self.total_energy = VarLine("Total energy delivered", None, display_decimals=2,  wide=True, inform_only=True, right_align=False, units={'J/cm²':1}, unit_width=38, name='tot energy')
#         self.total_energy.var.setRange(0,1e9)
#         self.illum_duration.var.setRange(0, 1e18)
#         self.total_duration.var.setRange(0, 1e18)
#
#         self.init_ui()
#         self.load_params(params)
#
#     def update_calc(self):
#         self.repetition_time.setMinimum(self.on_duration.getValue())
#         self.illum_duration.setValue(self.on_duration.getValue()*self.num_reps.getValue())
#         self.total_energy.setValue(self.illum_duration.getValue() * self.irradiance.getValue() * 1e-3)
#         self.total_duration.setValue((self.on_duration.getValue()+self.repetition_time.getValue()*(self.num_reps.getValue()-1)))
#         params = {
#             'experiment config': {
#                 'folderpath': self.folderpath,
#                 'on duration': {'value': self.on_duration.getValue(unit=self.on_duration.unit), 'unit':self.on_duration.unit},
#                 'repetition time': {'value': self.repetition_time.getValue(unit=self.repetition_time.unit), 'unit':self.repetition_time.unit},
#                 'num. illums': self.num_reps.getValue(),
#                 'Laser irradiance (mW/cm²)': self.irradiance.getValue(),
#             }
#         }
#         self.params_for_graph.emit(params)
#         return
#
#     def irr_calc(self):
#         self.irr_calc_window = PowerCalc(distance=self.distance_read, laser_power=self.laser_power)
#         self.irr_calc_window.setFont(QFont("Arial", 8))
#         self.irr_calc_window.irradiance_emit.connect(self.update_irradiance)
#         self.irr_calc_window.show()
#
#     @pyqtSlot(tuple)
#     def update_irradiance(self, values):
#         distance_read, power, irradiance = values
#         self.distance_read = distance_read
#         self.laser_power = power
#         self.irradiance.setValue(irradiance)
#
#     def init_ui(self):
#         self.frame = QFrame()
#         self.grid = QGridLayout()
#
#         self.start_btn = QPushButton('Start', clicked=self.go)
#         experiment_box = QGridLayout()
#         label = QLabel('PBM session parameters')
#         label.setStyleSheet("QLabel {font: bold 8pt;}")
#         experiment_box.addWidget(label, 0, 0, 1, 2)
#         experiment_box.addLayout(self.on_duration, 1, 0, 1, 2)
#         experiment_box.addLayout(self.repetition_time, 2, 0, 1, 2)
#         experiment_box.addLayout(self.num_reps, 3, 0, 1, 2)
#         experiment_box.addWidget(self.irr_calc_btn, 4, 0, 1, 1)
#         self.irr_calc_btn.setFixedSize(QSize(55,22))
#         experiment_box.addLayout(self.irradiance, 4, 1, 1, 1)
#
#         experiment_box.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 1, 2, 5, 1)
#
#         label_2 = QLabel('With these parameters, you will get:')
#         label_2.setStyleSheet("QLabel {font-size: 8pt;}")
#         experiment_box.addWidget(label_2, 1, 3, 1, 1)
#         experiment_box.addLayout(self.illum_duration, 2,3, 1, 1)
#         experiment_box.addLayout(self.total_energy, 3,3, 1, 1)
#         experiment_box.addLayout(self.total_duration, 4,3, 1, 1)
#
#
#         self.frame.setLayout(experiment_box)
#         self.frame.setLineWidth(1)
#         self.frame.setFrameStyle(0x0001)
#
#         self.grid.addWidget(self.frame)
#         # self.grid.setSizeConstraint(3)
#         self.setLayout(self.grid)
#
#     def select_dir(self):
#         self.folderpath = QFileDialog.getExistingDirectory(self, 'Select Folder for saving images',
#                                                            directory=self.folderpath)
#         print('Selected folder for saving : ' + self.folderpath)
#
#     def load_params(self, params=None):
#         if params is None:
#             with open(self.folderpath+r"/expmt_params.json", 'r') as f:
#                 params = json.load(f)
#             f.close()
#         try:
#             if self.first_setup:
#                 self.folder_path = default_folder
#             else:
#                 self.folderpath = params['experiment config']['folderpath']
#
#             self.on_duration.setValue(params['experiment config']['on duration']['value'], unit=params['experiment config']['on duration']['unit'])
#             self.repetition_time.setValue(params['experiment config']['repetition time']['value'], unit=params['experiment config']['repetition time']['unit'])
#             self.num_reps.setValue(params['experiment config']['num. illums'])
#             self.irradiance.setValue(params['experiment config']['Laser irradiance (mW/cm²)'])
#             self.distance_read = params['experiment config']['distance read']
#             self.laser_power = params['experiment config']['laser power']
#
#             self.update_calc()
#         except:
#             print('input params not readable')
#
#     def save_params(self, file=True):
#         filename = self.folderpath + r"/" + time.strftime("%Y%m%d_%H%M%S") + r"_expmt_params.json"
#         params = {
#             'experiment config':{
#                 'folderpath': self.folderpath,
#                 'on duration': {'value': self.on_duration.getValue(unit=self.on_duration.unit), 'unit':self.on_duration.unit},
#                 'repetition time': {'value': self.repetition_time.getValue(unit=self.repetition_time.unit), 'unit':self.repetition_time.unit},
#                 'num. illums': self.num_reps.getValue(),
#                 'Laser irradiance (mW/cm²)': self.irradiance.getValue(),
#                 'distance read': self.distance_read,
#                 'laser power': self.laser_power,
#                 'filename': filename
#             }
#         }
#         if file:
#             with open(self.folderpath+r"/expmt_params.json", 'w') as f:
#                 json.dump(params, f, indent=4)
#             f.close()
#             with open(self.folderpath+r"/"+time.strftime("%Y%m%d_%H%M%S")+r"_expmt_params.json", 'w') as f:
#                 json.dump(params, f, indent=4)
#             f.close()
#         return params
#
#     def close(self):
#         if self.irr_calc_window is not None:
#             self.irr_calc_window.close()
#         super().close()


# class ExpmtSetup_embedded_TotalTime(QWidget):
#     params_changed = pyqtSignal(dict)
#     params_for_graph = pyqtSignal(dict)
#     go_time = pyqtSignal()
#
#     def go(self):
#         params = self.save_params(file=True)
#         self.params_changed.emit(params)
#         self.params_for_graph.emit(params)
#         self.go_time.emit()
#
#     def cancel(self):
#         params = self.save_params(file=False)
#         self.params_changed.emit(params)
#         self.params_for_graph.emit(params)
#         self.close()
#
#     def __init__(self, parent_app, instr_list, params=None, first_setup=False, expmt_graph=None):
#         super().__init__()
#         self.parent_app = parent_app
#         controls = extract_controls(parent_app, instr_list)
#         if expmt_graph is not None:
#             self.params_for_graph.connect(expmt_graph.update_data)
#         self.first_setup = first_setup
#         try:
#             self.laser_control = controls['laser']
#         except:
#             print('missing laser controller')
#
#         self.setLocale(QLocale('C'))
#
#         """ timing parameters """
#         self.folderpath = default_folder
#         self.btn_select_dir = QPushButton('Select saving directory')
#         self.btn_select_dir.clicked.connect(self.select_dir)
#         self.btn_select_dir.setFixedWidth(80)
#
#         self.on_duration = VarLine("Duration of each illumination", None, display_decimals=1, tracked=True, wide=True,
#                                    right_align=False, units=time_units, name='on duration')
#         self.repetition_time = VarLine("Delay between illuminations", None, display_decimals=1, tracked=True, wide=True,
#                                        inform_only=True, right_align=False, units=time_units, name='rep time')
#         self.num_reps = VarLine("Number of illuminations in session", None, decimals=0, tracked=True, wide=True,
#                                 right_align=False, name='num reps')
#         self.total_duration = VarLine("Total duration of session", None, display_decimals=1, wide=True,
#                                       right_align=False, units=time_units, name='tot duration')
#
#         self.on_duration.var.setRange(0., 1e18)
#         self.repetition_time.var.setRange(0., 1e18)
#         self.num_reps.var.setRange(0, 100000)
#         self.on_duration.var.valueChanged.connect(self.update_calc)
#         self.total_duration.var.valueChanged.connect(self.update_calc)
#         self.num_reps.var.valueChanged.connect(self.update_calc)
#
#         self.distance_read = 0.
#         self.laser_power = 20
#
#         self.irradiance = VarLine("Irradiance", None, decimals=1, tracked=True, wide=True, right_align=False,
#                                   units={"mW/cm²": 1}, unit_width=50, name='irradiance', inform_only=True)
#         self.irradiance.var.setRange(0, 100)
#         self.irradiance.var.valueChanged.connect(self.update_calc)
#         self.irradiance.setToolTip(
#             "Indicate laser irradiance here, from YOUR knowledge of it.\nUseful for logging experiments, but WILL NOT change the laser power by itself.")
#
#         self.irr_calc_btn = QPushButton('Compute')
#         self.irr_calc_btn.clicked.connect(self.irr_calc)
#
#         self.illum_duration = VarLine("Total duration of illumination", None, display_decimals=1, wide=True,
#                                       inform_only=True, right_align=False, units=time_units, name='illum duration')
#         self.total_energy = VarLine("Total energy delivered", None, display_decimals=2, wide=True, inform_only=True,
#                                     right_align=False, units={'J/cm²': 1}, unit_width=38, name='tot energy')
#         self.total_energy.var.setRange(0, 1e9)
#         self.illum_duration.var.setRange(0, 1e18)
#         self.total_duration.var.setRange(0, 1e18)
#
#         self.init_ui()
#         self.load_params(params)
#
#     def update_calc(self):
#         self.repetition_time.setMinimum(self.on_duration.getValue())
#         self.total_duration.setMinimum(self.on_duration.getValue() * self.num_reps.getValue())
#         if self.num_reps.getValue() > 1:
#             delay = (self.total_duration.getValue() - self.on_duration.getValue()) / (self.num_reps.getValue() - 1)
#         else:
#             delay = 0.
#         self.repetition_time.setValue(delay)
#
#         self.illum_duration.setValue(self.on_duration.getValue() * self.num_reps.getValue())
#         self.total_energy.setValue(self.illum_duration.getValue() * self.irradiance.getValue() * 1e-3)
#         # self.total_duration.setValue((self.on_duration.getValue()+self.repetition_time.getValue()*(self.num_reps.getValue()-1)))
#         params = {
#             'experiment config': {
#                 'folderpath': self.folderpath,
#                 'on duration': {'value': self.on_duration.getValue(unit=self.on_duration.unit),
#                                 'unit': self.on_duration.unit},
#                 'total duration': {'value': self.total_duration.getValue(unit=self.total_duration.unit),
#                                    'unit': self.total_duration.unit},
#                 'repetition time': {'value': self.repetition_time.getValue(unit=self.repetition_time.unit),
#                                     'unit': self.repetition_time.unit},
#                 'num. illums': self.num_reps.getValue(),
#                 'Laser irradiance (mW/cm²)': self.irradiance.getValue(),
#             }
#         }
#         self.params_for_graph.emit(params)
#         return
#
#     def irr_calc(self):
#         self.irr_calc_window = PowerCalc(distance=self.distance_read, laser_power=self.laser_power)
#         self.irr_calc_window.setFont(QFont("Arial", 8))
#         self.irr_calc_window.irradiance_emit.connect(self.update_irradiance)
#         self.irr_calc_window.show()
#
#     @pyqtSlot(tuple)
#     def update_irradiance(self, values):
#         distance_read, power, irradiance = values
#         self.distance_read = distance_read
#         self.laser_power = power
#         self.irradiance.setValue(irradiance)
#
#     def init_ui(self):
#         self.frame = QFrame()
#         self.grid = QGridLayout()
#
#         self.start_btn = QPushButton('Start', clicked=self.go)
#         experiment_box = QGridLayout()
#         label = QLabel('PBM session parameters')
#         label.setStyleSheet("QLabel {font: bold 8pt;}")
#         experiment_box.addWidget(label, 0, 0, 1, 2)
#         experiment_box.addLayout(self.on_duration, 1, 0, 1, 2)
#         experiment_box.addLayout(self.total_duration, 2, 0, 1, 2)
#         experiment_box.addLayout(self.num_reps, 3, 0, 1, 2)
#         experiment_box.addWidget(self.irr_calc_btn, 4, 0, 1, 1)
#         self.irr_calc_btn.setFixedSize(QSize(55, 22))
#         experiment_box.addLayout(self.irradiance, 4, 1, 1, 1)
#
#         experiment_box.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 1, 2, 5, 1)
#
#         label_2 = QLabel('With these parameters, you will get:')
#         label_2.setStyleSheet("QLabel {font-size: 8pt;}")
#         experiment_box.addWidget(label_2, 1, 3, 1, 1)
#         experiment_box.addLayout(self.illum_duration, 2, 3, 1, 1)
#         experiment_box.addLayout(self.total_energy, 3, 3, 1, 1)
#         experiment_box.addLayout(self.repetition_time, 4, 3, 1, 1)
#
#         self.frame.setLayout(experiment_box)
#         self.frame.setLineWidth(1)
#         self.frame.setFrameStyle(0x0001)
#
#         self.grid.addWidget(self.frame)
#         # self.grid.setSizeConstraint(3)
#         self.setLayout(self.grid)
#
#     def select_dir(self):
#         self.folderpath = QFileDialog.getExistingDirectory(self, 'Select Folder for saving images',
#                                                            directory=self.folderpath)
#         print('Selected folder for saving : ' + self.folderpath)
#
#     def load_params(self, params=None):
#         if params is None:
#             with open(self.folderpath + r"/expmt_params.json", 'r') as f:
#                 params = json.load(f)
#             f.close()
#         try:
#             if self.first_setup:
#                 self.folder_path = default_folder
#             else:
#                 self.folderpath = params['experiment config']['folderpath']
#
#             self.on_duration.setValue(params['experiment config']['on duration']['value'],
#                                       unit=params['experiment config']['on duration']['unit'])
#             self.total_duration.setValue(params['experiment config']['total duration']['value'],
#                                          unit=params['experiment config']['total duration']['unit'])
#             self.repetition_time.setValue(params['experiment config']['repetition time']['value'],
#                                           unit=params['experiment config']['repetition time']['unit'])
#             self.num_reps.setValue(params['experiment config']['num. illums'])
#             self.irradiance.setValue(params['experiment config']['Laser irradiance (mW/cm²)'])
#             self.distance_read = params['experiment config']['distance read']
#             self.laser_power = params['experiment config']['laser power']
#
#             self.update_calc()
#         except:
#             print('input params not readable')
#
#     def save_params(self, file=True):
#         filename = self.folderpath + r"/" + time.strftime("%Y%m%d_%H%M%S") + r"_expmt_params.json"
#         params = {
#             'experiment config': {
#                 'folderpath': self.folderpath,
#                 'on duration': {'value': self.on_duration.getValue(unit=self.on_duration.unit),
#                                 'unit': self.on_duration.unit},
#                 'total duration': {'value': self.total_duration.getValue(unit=self.total_duration.unit),
#                                    'unit': self.total_duration.unit},
#                 'repetition time': {'value': self.repetition_time.getValue(unit=self.repetition_time.unit),
#                                     'unit': self.repetition_time.unit},
#                 'num. illums': self.num_reps.getValue(),
#                 'Laser irradiance (mW/cm²)': self.irradiance.getValue(),
#                 'distance read': self.distance_read,
#                 'laser power': self.laser_power,
#                 'filename': filename
#             }
#         }
#         if file:
#             with open(self.folderpath + r"/expmt_params.json", 'w') as f:
#                 json.dump(params, f, indent=4)
#             f.close()
#             with open(self.folderpath + r"/" + time.strftime("%Y%m%d_%H%M%S") + r"_expmt_params.json", 'w') as f:
#                 json.dump(params, f, indent=4)
#             f.close()
#         return params
#
#     def close(self):
#         if self.irr_calc_window is not None:
#             self.irr_calc_window.close()
#         super().close()

class ExpmtSetup_embedded_TotalTime_TotalIllumDuration(QWidget):
    params_changed = pyqtSignal(dict)
    params_for_graph = pyqtSignal(dict)
    go_time = pyqtSignal()

    def go(self):
        params = self.save_params(file=True)
        self.params_changed.emit(params)
        self.params_for_graph.emit(params)
        self.go_time.emit()

    def cancel(self):
        params = self.save_params(file=False)
        self.params_changed.emit(params)
        self.params_for_graph.emit(params)
        self.close()

    def __init__(self, parent_app, instr_list, params=None, first_setup=False, expmt_graph=None):
        super().__init__()
        self.parent_app = parent_app
        controls = extract_controls(parent_app, instr_list)
        if expmt_graph is not None:
            self.params_for_graph.connect(expmt_graph.update_data)
        self.first_setup = first_setup
        try:
            self.laser_control = controls['laser']
        except:
            print('missing laser controller')

        self.setLocale(QLocale('C'))

        """ timing parameters """
        self.folderpath = default_folder
        self.btn_select_dir = QPushButton('Select saving directory')
        self.btn_select_dir.clicked.connect(self.select_dir)
        self.btn_select_dir.setFixedWidth(80)

        self.illum_duration = VarLine("Total duration of illumination", None, display_decimals=1, wide=True,
                                      right_align=False, units=time_units, name='illum duration')
        self.num_reps = VarLine("Number of illuminations in session", None, decimals=0, tracked=True, wide=True,
                                right_align=False, name='num reps')
        self.total_duration = VarLine("Total duration of session", None, display_decimals=1, wide=True,
                                      right_align=False, units=time_units, name='tot duration')

        self.illum_duration.var.setRange(0., 1e18)
        self.num_reps.var.setRange(0, 100000)
        self.illum_duration.var.valueChanged.connect(self.update_calc)
        self.total_duration.var.valueChanged.connect(self.update_calc)
        self.num_reps.var.valueChanged.connect(self.update_calc)

        self.distance_read = 0.
        self.laser_power = 20
        self.laser_source = None

        self.irradiance = VarLine("Irradiance", None, decimals=1, tracked=True, wide=True, right_align=False,
                                  units={"mW/cm²": 1}, unit_width=50, name='irradiance', inform_only=True)
        self.irradiance.var.setRange(0, 100)
        self.irradiance.var.valueChanged.connect(self.update_calc)
        self.irradiance.setToolTip(
            "Compute with the \"Compute\" button to the left, using the distance read on the ruler and the setting on the laser.\nUseful for calculating doses and logging experiments, but WILL NOT change the laser power by itself.")

        self.irr_calc_btn = QPushButton('Compute')
        self.irr_calc_btn.clicked.connect(self.irr_calc)
        self.irr_calc_btn.setToolTip(
            "Compute with this button, using the distance read on the ruler and the setting on the laser.\nUseful for calculating doses and logging experiments, but WILL NOT change the laser power by itself.")

        self.total_energy = VarLine("Total energy delivered", None, display_decimals=2, wide=True, inform_only=True,
                                    right_align=False, units={'J/cm²': 1}, unit_width=38, name='tot energy')

        self.on_duration = VarLine("Duration of each illumination", None, display_decimals=1, tracked=True, wide=True,
                                        inform_only=True, right_align=False, units=time_units, name='on duration')
        self.repetition_time = VarLine("Repetition time", None, display_decimals=1, tracked=True, wide=True,
                                       inform_only=True, right_align=False, units=time_units, name='rep time')

        self.total_energy.var.setRange(0, 1e9)
        self.on_duration.var.setRange(0, 1e18)
        self.repetition_time.var.setRange(0., 1e18)
        self.total_duration.var.setRange(0, 1e18)

        self.laser_source_label = QLabel("Laser source: not selected")
        self.laser_source_label.setStyleSheet("QLabel {font: bold 8pt; background-color: rgb(200,200,200); color: rgb(255,0,0)}")
        self.laser_source_label.setFixedWidth(205)

        self.init_ui()
        self.irr_calc_window=None
        self.load_params(params)

    @pyqtSlot(str)
    def update_laser_source(self, new_source):
        self.laser_source = new_source
        if new_source is not None:
            self.laser_source_label.setText("Laser source: "+new_source)
        else:
            self.laser_source_label.setText("Laser source: not selected")

    def update_calc(self):
        self.update_laser_source(self.laser_source)
        # self.repetition_time.setMinimum(self.on_duration.getValue())
        self.total_duration.setMinimum(self.illum_duration.getValue())

        if self.num_reps.getValue() > 0:
            self.on_duration.setValue(self.illum_duration.getValue()/self.num_reps.getValue())
        else:
            self.on_duration.setValue(0.)

        if self.num_reps.getValue() > 1:
            delay = (self.total_duration.getValue() - self.on_duration.getValue()) / (self.num_reps.getValue() - 1)
        else:
            delay = self.total_duration.getValue()
        self.repetition_time.setValue(delay)

        # self.illum_duration.setValue(self.on_duration.getValue() * self.num_reps.getValue())
        self.total_energy.setValue(self.illum_duration.getValue() * self.irradiance.getValue() * 1e-3)
        # self.total_duration.setValue((self.on_duration.getValue()+self.repetition_time.getValue()*(self.num_reps.getValue()-1)))
        params = {
            'experiment config': {
                'folderpath': self.folderpath,
                'on duration': {'value': self.on_duration.getValue(unit=self.on_duration.unit),
                                'unit': self.on_duration.unit},
                'total duration': {'value': self.total_duration.getValue(unit=self.total_duration.unit),
                                   'unit': self.total_duration.unit},
                'repetition time': {'value': self.repetition_time.getValue(unit=self.repetition_time.unit),
                                    'unit': self.repetition_time.unit},
                'num. illums': self.num_reps.getValue(),
                'illum duration': {'value': self.illum_duration.getValue(unit=self.illum_duration.unit),
                                   'unit': self.illum_duration.unit},
                'Laser irradiance (mW/cm²)': self.irradiance.getValue(),
                'Laser source': None,
            }
        }
        self.params_for_graph.emit(params)
        return

    def irr_calc(self):
        self.irr_calc_window = PowerCalc(distance=self.distance_read, laser_power=self.laser_power, laser_source=self.laser_source)
        self.irr_calc_window.laser_list.currentTextChanged.connect(self.update_laser_source)
        self.irr_calc_window.setFont(QFont("Arial", 8))
        self.irr_calc_window.irradiance_emit.connect(self.update_irradiance)
        self.irr_calc_window.show()

    @pyqtSlot(tuple)
    def update_irradiance(self, values):
        distance_read, power, irradiance = values
        self.distance_read = distance_read
        self.laser_power = power
        self.irradiance.setValue(irradiance)
        self.irr_calc_window = None

    def init_ui(self):
        self.frame = QFrame()
        self.grid = QGridLayout()

        self.start_btn = QPushButton('Start', clicked=self.go)
        experiment_box = QGridLayout()
        label = QLabel('PBM session parameters')
        label.setStyleSheet("QLabel {font: bold 8pt;}")
        experiment_box.addWidget(label, 0, 0, 1, 2)
        experiment_box.addWidget(self.laser_source_label, 0, 2, 1, 3, Qt.AlignRight)
        experiment_box.addLayout(self.illum_duration, 1, 0, 1, 2)
        experiment_box.addLayout(self.total_duration, 2, 0, 1, 2)
        experiment_box.addLayout(self.num_reps, 3, 0, 1, 2)
        experiment_box.addWidget(self.irr_calc_btn, 4, 0, 1, 1)
        self.irr_calc_btn.setFixedSize(QSize(55, 22))
        experiment_box.addLayout(self.irradiance, 4, 1, 1, 1)

        experiment_box.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding), 1, 2, 5, 1)

        label_2 = QLabel('With these parameters, you will get:')
        label_2.setStyleSheet("QLabel {font-size: 8pt;}")
        experiment_box.addWidget(label_2, 1, 3, 1, 1)
        experiment_box.addLayout(self.total_energy, 2, 3, 1, 1)
        experiment_box.addLayout(self.on_duration, 3, 3, 1, 1)
        experiment_box.addLayout(self.repetition_time, 4, 3, 1, 1)

        self.frame.setLayout(experiment_box)
        self.frame.setLineWidth(1)
        self.frame.setFrameStyle(0x0001)

        self.grid.addWidget(self.frame)
        # self.grid.setSizeConstraint(3)
        self.setLayout(self.grid)

    def select_dir(self):
        self.folderpath = QFileDialog.getExistingDirectory(self, 'Select Folder for saving images',
                                                           directory=self.folderpath)
        print('Selected folder for saving : ' + self.folderpath)

    def load_params(self, params=None):
        if params is None:
            with open(self.folderpath + r"/expmt_params.json", 'r') as f:
                params = json.load(f)
            f.close()
        try:
            if self.first_setup:
                self.folder_path = default_folder
            else:
                self.folderpath = params['experiment config']['folderpath']

            self.on_duration.setValue(params['experiment config']['on duration']['value'],
                                      unit=params['experiment config']['on duration']['unit'])
            self.total_duration.setValue(params['experiment config']['total duration']['value'],
                                         unit=params['experiment config']['total duration']['unit'])
            self.repetition_time.setValue(params['experiment config']['repetition time']['value'],
                                          unit=params['experiment config']['repetition time']['unit'])
            self.illum_duration.setValue(params['experiment config']['illum duration']['value'],
                                         unit=params['experiment config']['illum duration']['unit'])
            self.num_reps.setValue(params['experiment config']['num. illums'])
            self.irradiance.setValue(params['experiment config']['Laser irradiance (mW/cm²)'])
            self.distance_read = params['experiment config']['distance read']
            self.laser_power = params['experiment config']['laser power']
            try:
                self.laser_source = params['experiment config']['laser source']
            except KeyError:
                self.laser_source = None

            self.update_calc()
        except:
            print('input params not readable')

    def save_params(self, file=True):
        filename = self.folderpath + r"/" + time.strftime("%Y%m%d_%H%M%S") + r"_expmt_params.json"
        params = {
            'experiment config': {
                'folderpath': self.folderpath,
                'on duration': {'value': self.on_duration.getValue(unit=self.on_duration.unit),
                                'unit': self.on_duration.unit},
                'total duration': {'value': self.total_duration.getValue(unit=self.total_duration.unit),
                                   'unit': self.total_duration.unit},
                'repetition time': {'value': self.repetition_time.getValue(unit=self.repetition_time.unit),
                                    'unit': self.repetition_time.unit},
                'num. illums': self.num_reps.getValue(),
                'illum duration': {'value':self.illum_duration.getValue(unit=self.illum_duration.unit),
                                   'unit': self.illum_duration.unit},
                'Laser irradiance (mW/cm²)': self.irradiance.getValue(),
                'distance read': self.distance_read,
                'laser power': self.laser_power,
                'laser source': self.laser_source,
                'filename': filename
            }
        }
        if file:
            with open(self.folderpath + r"/expmt_params.json", 'w') as f:
                json.dump(params, f, indent=4)
            f.close()
            with open(self.folderpath + r"/" + time.strftime("%Y%m%d_%H%M%S") + r"_expmt_params.json", 'w') as f:
                json.dump(params, f, indent=4)
            f.close()
        return params

    def close(self):
        if self.irr_calc_window is not None:
            self.irr_calc_window.close()
        super().close()