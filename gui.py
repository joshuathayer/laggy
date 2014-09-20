import sys
from PyQt4 import QtCore, QtGui

class LaggyGui(QtGui.QMainWindow):
    STATE_IDLE = 0
    STATE_RECORDING = 1

    def addLine(self, msg):
        self.log(msg)

    def __init__(self, reactor, parent=None):
        super(LaggyGui, self).__init__(parent)
        self.reactor=reactor
        
        self.recorder = None

        self.state = self.STATE_IDLE
        # self.setWindowTitle('Laggy')

        # XXX: some day you will have an icon :)
        #self.setWindowIcon(window_icon)

        # message log
        self.message_log = QtGui.QListWidget()

        # record button
        self.button = QtGui.QPushButton('Record Message')
        self.button.clicked.connect(self.button_clicked)

        # main layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.message_log)
        layout.addWidget(self.button)

        main_frame = QtGui.QWidget()
        main_frame.setLayout(layout)

        self.setCentralWidget(main_frame)

        self.log('Check it out, you can log messages')

    def button_clicked(self):
        self.log('The button was clicked')

        if self.state == self.STATE_IDLE:
            self.state = self.STATE_RECORDING
            self.button.setText('Stop Recording')
            # XXX: start recording
            self.log('Recording should start now')
            self.recorder.toggle()

        elif self.state == self.STATE_RECORDING:
            self.state = self.STATE_IDLE
            self.button.setText('Record Message')
            self.log('Recording should stop now')
            # XXX: stop recording
            self.recorder.toggle()


    def log(self, msg):
        item = QtGui.QListWidgetItem(msg)
        self.message_log.addItem(item)
