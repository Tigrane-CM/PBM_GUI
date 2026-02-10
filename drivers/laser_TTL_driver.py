try:
    import RPi.GPIO as GPIO
except:
    print("no GPIO module found")
from time import sleep, time
from sys import platform

class LED:
    def __init__(self, pin):
        self.pin=pin
        self.active_high=True
        self.is_active=True

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.off()

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH)
        self.is_active=True

    def off(self):
        GPIO.output(self.pin, GPIO.LOW)
        self.is_active=False

class LED_:
    def __init__(self, port):
        self.active_high=True
        self.is_active=False

    def on(self):
        self.is_active=True
        return

    def off(self):
        self.is_active=False
        return

    def blink(self, pulse_duration=1, total_duration=10):
        prev_state = self.is_active
        if prev_state:
            self.off()

        start = time()
        while time()-start < total_duration:
            self.on()
            sleep(pulse_duration)
            self.off()
            sleep(pulse_duration)
        if prev_state:
            self.on()
        else:
            self.off()
        return


class LaserTTL:
    def __init__(self, pin=23):
        self.pin = pin
        try:
            self.TTL = LED(self.pin)
        except:
            print("no LED class defined, using dummy")
            if platform == 'win32':
                self.TTL = LED_(self.pin)
            else:
                raise IOError("GPIO pin not available, closing.")
        self.is_active = self.TTL.is_active

    def on(self, duration=0.):
        self.TTL.on()
        self.update_state()
        if duration > 0.: # FIXME: will freeze everything during wait
            sleep(duration)
            self.TTL.off()
        return

    def off(self):
        self.TTL.off()
        self.update_state()
        return

    def update_state(self):
        self.is_active = self.TTL.is_active
        return

    def close(self):
        self.off()
        return