import time

from PyQt5.QtCore import QLocale, Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtWidgets import (QWidget, QLabel, QFrame, QGridLayout, QSizePolicy, QPushButton, QApplication,
                             QSpacerItem, QMessageBox)

import win_inhibitor
import sys

from drivers import LaserTTL
from controllers import LaserTTLController
from timed_experiment import ExpControl, ExpmtSetup_embedded_TotalTime_TotalIllumDuration # ,ExpmtSetup_embedded, ExpmtSetup_embedded_TotalTime
from UIs import ExpmtGraph, LiveGraph


class PBMSplash(QWidget):
    def __init__(self):
        super().__init__()
        self.setLocale(QLocale('C'))
        self.setWindowFlags(Qt.SplashScreen | Qt.WindowTransparentForInput)

        splash_label = QLabel()
        splash_label.setText('Welcome to PBM GUI...\nplease wait !')
        splash_label.setAlignment(Qt.AlignCenter)
        font = splash_label.font()
        font.setPointSize(18)
        splash_label.setFont(font)
        splash_label.setStyleSheet("QLabel {color : rgb(60,60,60);}")

        self.instr_label = QLabel()
        self.instr_label.setText('initializing')
        font = self.instr_label.font()
        font.setPointSize(14)
        self.instr_label.setFont(font)
        self.instr_label.setStyleSheet("QLabel {color : rgb(60,60,60);}")

        label_frame = QFrame()
        label_layout = QGridLayout()
        label_layout.addWidget(splash_label, 0, 0, 1, 1, Qt.AlignCenter)
        label_layout.addWidget(self.instr_label, 1, 0, 1, 1, Qt.AlignCenter)
        label_frame.setLayout(label_layout)
        label_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        label_frame.setStyleSheet("QFrame {background-color: lightGray;}")
        label_frame.setFixedSize(300, 100)
        label_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        image_label = QLabel()
        splash_pixmap = QPixmap('splash_image.png')
        image_label.setPixmap(splash_pixmap.scaledToWidth(600))

        splash_layout = QGridLayout()
        splash_layout.addWidget(image_label, 0, 0, 3, 3)
        splash_layout.addWidget(label_frame, 1, 1, 1, 1)

        self.setLayout(splash_layout)

    def receive(self, instr_name):
        self.instr_label.setText('initializing ' + instr_name)
        if instr_name == 'Phasics':
            self.instr_label.setText('initializing Phasics, takes time')

class PBMGui(QWidget):
    def __init__(self, splash_=None, parent=None):
        super().__init__()
        self.setWindowTitle("PBM Precision Laser Control")
        self.setLocale(QLocale('C'))

        if parent:
            self.parent_app = parent
        if splash_:
            self.splash = splash_

        self.dummy_allowed = True

        self.win_unsleep_flag = False
        self.win_unsleep_btn = QPushButton()

        try:
            self.laser_TTL_driver = LaserTTL()
        except IOError as exception:
            if QMessageBox.Ok == QMessageBox.warning(self, "Exiting", "GPIO pin not available, exiting!\n(check that no other instance of this app is open)", QMessageBox.Ok):
                self.closeEvent()
        self.live_graph = LiveGraph()
        self.live_graph.setFixedWidth(460)
        self.laser_controller = LaserTTLController(self.laser_TTL_driver, live_graph=self.live_graph)

        self.expmt_graph = ExpmtGraph()
        self.expmt_graph.setFixedWidth(460)
        self.emb_setup = ExpmtSetup_embedded_TotalTime_TotalIllumDuration(self, ['laser'], params=None, first_setup=True, expmt_graph=self.expmt_graph)
        self.emb_setup.setFixedWidth(460)
        self.experiment_control = ExpControl(self, instr_list=['laser'], expmt_graph=self.expmt_graph, emb_setup=self.emb_setup)
        self.experiment_control.setFixedWidth(335)
        self.experiment_control.setFixedHeight(90)
        self.laser_controller.ui.setFixedHeight(90)

        self.init_ui()

    def init_ui(self):
        self.splash.receive('UI')
        self.parent_app.processEvents()

        control_layout = QGridLayout()

        # """ add windows unsleep button """
        # self.win_unsleep_btn.setText("Prevent Windows from sleeping")
        # self.win_unsleep_btn.clicked.connect(lambda: self.win_unsleep())

        control_layout.addWidget(self.laser_controller.ui, 1, 0, 1, 1, Qt.AlignCenter)
        control_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding), 1, 1, 1, 2)
        control_layout.addWidget(self.experiment_control, 1, 2, 1, 2, Qt.AlignCenter)
        control_layout.addWidget(self.emb_setup, 2, 0, 1, 4, Qt.AlignCenter)
        control_layout.addWidget(self.live_graph, 0, 0, 1, 4, Qt.AlignCenter)
        control_layout.addWidget(self.expmt_graph, 3, 0, 1, 4, Qt.AlignCenter)

        control_layout.setSpacing(2)
        control_layout.setSizeConstraint(3)

        layout = QGridLayout()
        layout.addLayout(control_layout, 0, 0)
        layout.setRowStretch(0, 1)
        layout.setColumnStretch(0, 1)

        self.setLayout(layout)

    def win_unsleep(self):
        if not self.win_unsleep_flag:
            win_inhibitor.prevent_sleep()
            self.win_unsleep_btn.setText("Authorize Windows sleep")
            self.win_unsleep_btn.setStyleSheet("background-color : lightblue;")
            self.win_unsleep_flag = True
        else:
            win_inhibitor.authorize_sleep()
            self.win_unsleep_btn.setText("Prevent Windows sleep")
            self.win_unsleep_btn.setStyleSheet("background-color : lightgray; border = 2px;")
            self.win_unsleep_flag = False
        return

    def closeEvent(self, e):
        e.ignore()
        if self.experiment_control.work_thread is not None:
            if QMessageBox.Yes == QMessageBox.warning(self, "Exit Confirmation", "An experiment is running!\nAre you sure you want to exit the program?", QMessageBox.Yes |QMessageBox.No):
                e.accept()
            else:
                return
        else:
            if QMessageBox.Yes == QMessageBox.question(self, "Exit Confirmation", "Are you sure you want to exit the program?", QMessageBox.Yes |QMessageBox.No):
                e.accept()
            else:
                return
        self.experiment_control.stop_work()
        self.laser_controller.off()
        self.emb_setup.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('./icon.png'))

    screen_geom = app.desktop().screenGeometry()

    splash = PBMSplash()

    # splash.setWindowFlag(Qt.WindowStaysOnTopHint)
    splash.show()
    x = int((screen_geom.width() - splash.width()) / 2)
    y = int((screen_geom.height() - splash.height()) / 2.2)
    splash.move(x, y)

    gui = PBMGui(splash_=splash, parent=app)
    gui.setFont(QFont("Arial", 8))
    gui.setFixedWidth(480)
    gui.setFixedHeight(740)
    gui.show()
    x = int((screen_geom.width() - gui.width()) / 2)
    y = int((screen_geom.height() - gui.height()) / 2.5)
    gui.move(x, y)
    splash.close()
    gui.activateWindow()
    gui.raise_()

    sys.exit(app.exec_())
