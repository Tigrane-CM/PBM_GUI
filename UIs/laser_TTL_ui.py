from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QFrame, QLabel
from qt_mods import ToggleButton


class LaserTTLUI(QWidget):
    def __init__(self, control):
        self.control = control
        self.state = False
        super().__init__()

        label = QLabel("Laser control")
        label.setStyleSheet("QLabel {font: bold 8pt;}")
        self.toggle = ToggleButton()
        self.btn = QPushButton('OFF')
        self.btn.setDisabled(True)
        self.toggle.clicked.connect(self.control.toggle)
        self.btn.setFixedWidth(40)


        self.grid = QGridLayout()
        self.control_frame = QFrame()
        control_box = QGridLayout()
        control_box.setSpacing(2)

        control_box.addWidget(label, 0, 0, 1, 2, Qt.AlignCenter)
        control_box.addWidget(self.toggle, 1, 0, 1, 1)
        control_box.addWidget(self.btn, 1, 1, 1, 1)
        control_box.setRowStretch(1, 1)

        self.control_frame.setLayout(control_box)
        self.control_frame.setLineWidth(1)
        self.control_frame.setFrameStyle(0x0001)

        self.grid.addWidget(self.control_frame)
        self.grid.setSizeConstraint(3)
        self.setLayout(self.grid)

    def update(self, value):
        self.toggle.start_transition(value)
        if value:
            self.btn.setText('ON')
            self.btn.setStyleSheet("color: red")

        else:
            self.btn.setText('OFF')
            self.btn.setStyleSheet("color: black")


    def closeEvent(self):
        print("closing laser UI")
        if self.control is not None:
            self.control.closeEvent()