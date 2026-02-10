from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation, QPoint, QRect, pyqtSlot, pyqtSignal, pyqtProperty
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QDoubleSpinBox, QSizePolicy, QLabel, QSpacerItem, QCheckBox,QComboBox, QStyleOptionComboBox, QStyle)
from string import Template


class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d).replace(' ','')

class Closable(QWidget):
    closing = pyqtSignal()

    def closeEvent(self, e):
        self.closing.emit()
        super().closeEvent(e)

class NoArrowCombo(QComboBox):
    def paintEvent(self, e, QPaintEvent=None):
        p=QPainter()
        p.begin(self)
        opt = QStyleOptionComboBox()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_PanelButtonBevel, opt, p, self)
        self.style().drawPrimitive(QStyle.PE_PanelButtonCommand, opt, p, self)
        self.style().drawItemText(p, self.rect(), Qt.AlignCenter, self.palette(), self.isEnabled(), self.currentText())

class HighPrecisionDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, display_decimals=2):
        super().__init__()
        self.display_decimals = display_decimals
        self.setDecimals(16)

    def textFromValue(self, v):
        return f"{v:.{self.display_decimals:d}f}"

class VarLine(QHBoxLayout):
    def __init__(self, text, callback, decimals=0, tracked=False, wide=False, narrow=False, right_align=True, inform_only=False, **kwargs):  # , slow=False):
        super().__init__()
        self.setSpacing(1)

        self.inform_only = inform_only
        self.units = None
        self.unit = None
        self.unit_choice = None
        
        if 'name' in kwargs:
            self.name = kwargs['name']
            kwargs.pop('name')

        if "units" in kwargs:
            self.units = kwargs['units']
            self.unit = list(self.units.keys())[0]
            kwargs.pop('units')

            self.unit_choice = NoArrowCombo()
            self.unit_choice.addItems(list(self.units.keys()))
            self.unit_choice.setStyleSheet("QComboBox {font-size:8pt} QComboBox::drop-down {border-width: 0px;} QComboBox::down-arrow {image: url(noimg); border-width: 0px;}")
            self.unit_choice.setFixedWidth(30)
            self.unit_choice.setFixedHeight(18)
            if len(self.units)<2:
                self.unit_choice.setDisabled(True)
                self.unit_choice.setStyleSheet("QComboBox{background-color: white; color: black; font-size:8pt;}")
            if "unit_width" in kwargs:
                self.unit_choice.setFixedWidth(kwargs["unit_width"])
                kwargs.pop("unit_width")

        if not self.inform_only:
            if 'display_decimals' in kwargs:
                self.var = HighPrecisionDoubleSpinBox(display_decimals=kwargs['display_decimals'])
                kwargs.pop('display_decimals')
            else:
                self.var = QDoubleSpinBox(**kwargs)
                self.var.setDecimals(decimals)
            self.var.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        else:
            self.var = HighPrecisionDoubleSpinBox(**kwargs)
            self.var.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        if self.inform_only:
            self.var.setButtonSymbols(QDoubleSpinBox.NoButtons)
            self.var.setReadOnly(True)

        if callback is not None:
            self.var.valueChanged.connect(callback)
        if not tracked:
            self.var.setKeyboardTracking(False)

        # if not self.inform_only:
        self.var.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.var.setFixedWidth(30)
        self.var.setFixedHeight(18)
        self.label = QLabel(text)
        if not wide:
            self.label.setFixedWidth(30)
        if narrow:
            self.label.setFixedWidth(25)
        self.label.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        if not narrow:
            if right_align:
                self.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        self.addWidget(self.label, Qt.AlignLeft)
        if not right_align:
            self.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding))

        self.addWidget(self.var, Qt.AlignLeft)

        if self.units is not None:
            self.addWidget(self.unit_choice)
            self.unit_choice.currentTextChanged.connect(self.after_unit_change)
        else:
            self.units = {'none':1}
            self.unit='none'

    def getValue(self, unit=None):
        if unit is None:
            return self.var.value()*self.units[self.unit]
        else:
            return self.var.value()*self.units[self.unit]/self.units[unit]

    def setMinimum(self, new_min, unit=None):
        if unit is not None:
            self.change_units(unit)
            self.var.setMinimum(new_min)
        else:
            self.var.setMinimum(new_min/self.units[self.unit])
        # self.adapt_unit_inform_only()

    def setMaximum(self, new_max, unit=None):
        if unit is not None:
            self.change_units(unit)
            self.var.setMinimum(new_max)
        else:
            self.var.setMinimum(new_max/self.units[self.unit])
        # self.adapt_unit_inform_only()

    def setRange(self, new_min, new_max, unit=None):
        self.setMinimum(new_min, unit)
        self.setMaximum(new_max, unit)
        return

    def setValue(self, new_val, unit=None):
        if unit is not None:
            self.change_units(unit)
            self.var.setValue(new_val)
        else:
            self.var.setValue(new_val / self.units[self.unit])
        if self.inform_only:
            self.adapt_unit_inform_only()

    def change_units(self, new_unit):
        self.unit_choice.setCurrentText(new_unit)
        return

    @pyqtSlot(str)
    def after_unit_change(self, new_unit):
        old_val = self.var.value()
        old_min = self.var.minimum()
        old_max = self.var.maximum()
        raw_val = old_val * float(self.units[self.unit])
        raw_min = old_min * float(self.units[self.unit])
        raw_max = old_max * float(self.units[self.unit])
        new_val = raw_val / float(self.units[new_unit])
        new_min = raw_min / float(self.units[new_unit])
        new_max = raw_max / float(self.units[new_unit])
        self.unit = new_unit
        self.var.setRange(new_min, new_max)
        self.var.setValue(new_val)

    def adapt_unit_inform_only(self):
        value = self.var.value()
        for key in self.units.keys():
            if self.units[self.unit] < self.units[key]:
                if value*self.units[self.unit] > 1.5*self.units[key]:
                    self.unit_choice.setCurrentText(key)
                    break
            elif self.units[self.unit] > self.units[key]:
                if value*self.units[self.unit] < 1*self.units[self.unit]:
                    self.change_units(key)
                    break

    def setToolTip(self, *args):
        self.label.setToolTip(*args)
        self.var.setToolTip(*args)
        if self.unit_choice is not None:
            self.unit_choice.setToolTip(*args)


class ToggleButton(QCheckBox):
    def __init__(
            self,
            width=70,
            bgColor="#777",
            circleColor="#DDD",
            activeColor="red",
            animationCurve=QEasingCurve.OutCurve,):
        QCheckBox.__init__(self)

        # self.setFixedSize(QSize(width, 40))
        self._width = 40
        self._height = 20
        self.circle_diameter = int(0.8*self._height)
        self.setFixedWidth(self._width)
        self.setFixedHeight(self._height)
        self.setCursor(Qt.PointingHandCursor)

        self._bg_color = bgColor
        self._circle_color = circleColor
        self._active_color = activeColor
        self._circle_position = 2
        self.animation = QPropertyAnimation(self, b"circle_position")

        self.animation.setEasingCurve(animationCurve)
        self.animation.setDuration(500)
        # self.stateChanged.connect(self.start_transition)

    @pyqtProperty(int)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def start_transition(self, value):
        self.animation.setStartValue(self._circle_position)
        if value:
            self.animation.setEndValue(self.width() - self.circle_diameter-3)
        else:
            self.animation.setEndValue(3)
        self.setChecked(value)
        # self.animation.start()


    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e, value=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.setPen(Qt.NoPen)

        rect = QRect(0, 0, self.width(), self.height())
        if value is None:
            value = self.isChecked()
        if not value:
            p.setBrush(QColor(self._bg_color))
            p.drawRoundedRect(
                0, 0,
                rect.width(),
                self.height(),
                self.height() / 2,
                self.height() / 2
            )

            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(self._circle_position, 2, self.circle_diameter, self.circle_diameter)
        else:
            p.setBrush(QColor(self._active_color))
            p.drawRoundedRect(
                0, 0,
                rect.width(),
                self.height(),
                self.height() / 2,
                self.height() / 2
            )

            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(self.width() - self.circle_diameter-2, 2, self.circle_diameter, self.circle_diameter)
            # p.drawEllipse(self._circle_position, 3, self.circle_diameter, self.circle_diameter)
        return