from PyQt5.QtCore import QObject, pyqtSignal

from UIs import LaserTTLUI

class LaserTTLController(QObject):
    laser_on = pyqtSignal(bool)

    def __init__(self, laser_ttl, live_graph=None, ui_active=True, **kwargs):
        super().__init__(**kwargs)
        self.laser_TTL = laser_ttl
        self.state = False
        self.live_graph=live_graph
        self.laser_on.connect(self.live_graph.update_laser_state)

        if ui_active:
            self.ui = LaserTTLUI(self)
        else:
            pass

    def on(self):
        self.laser_TTL.on()
        self.update_state()
        return self.state

    def off(self):
        self.laser_TTL.off()
        self.update_state()
        return self.state

    def toggle(self):
        if self.state:
            return self.off()
        else:
            return self.on()

    def update_state(self):
        self.state = self.laser_TTL.is_active
        self.laser_on.emit(self.state)
        self.ui.update(self.state)
        return self.state

    def closeEvent(self):
        self.off()
        self.laser_ttl.close()