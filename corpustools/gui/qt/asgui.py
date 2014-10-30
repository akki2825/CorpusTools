
from PyQt5.QtCore import pyqtSignal as Signal,QThread
from PyQt5.QtWidgets import (QDialog, QListWidget, QGroupBox, QHBoxLayout,
                            QVBoxLayout, QPushButton, QFrame, QGridLayout,
                            QRadioButton, QLabel, QFormLayout, QLineEdit,
                            QFileDialog, QComboBox,QProgressDialog, QCheckBox)

from .widgets import DirectoryWidget, RadioSelectWidget
import os
import corpustools.acousticsim.main as AS

class ASWorker(QThread):
    updateProgress = Signal(str)

    dataReady = Signal(object)

    def __init__(self):
        QThread.__init__(self)

    def setParams(self, kwargs):
        self.kwargs = kwargs

    def run(self):
        kwargs = self.kwargs
        self.results = list()
        self.results.append(AS.acoustic_similarity_directories(**kwargs))
        self.dataReady.emit(self.results)

class ASDialog(QDialog):

    header = ['Directory 1',
            'Directory 2',
            'Representation',
            'Match function',
            'Minimum frequency',
            'Maximum frequency',
            'Number of filters',
            'Number of coefficients',
            'Result',
            'Is similarity?']
    def __init__(self, parent):
        QDialog.__init__(self, parent)

        layout = QVBoxLayout()

        aslayout = QHBoxLayout()

        directoryFrame = QGroupBox('Directories')
        box = QFormLayout()

        self.directoryOne = DirectoryWidget()
        self.directoryTwo = DirectoryWidget()
        box.addRow('First directory:',self.directoryOne)
        box.addRow('Second directory:',self.directoryTwo)

        directoryFrame.setLayout(box)

        aslayout.addWidget(directoryFrame)

        optionLayout = QVBoxLayout()

        self.representationWidget = RadioSelectWidget('Represenation',
                                                        {'MFCC':'mfcc',
                                                        'Amplitude envelopes':'envelopes'})

        optionLayout.addWidget(self.representationWidget)

        self.distAlgWidget = RadioSelectWidget('Distance algorithm',
                                                        {'Dynamic time warping':'dtw',
                                                        'Cross-correlation':'xcorr'})

        optionLayout.addWidget(self.distAlgWidget)

        freqLimFrame = QGroupBox('Frequency limits')

        box = QFormLayout()

        self.minFreqEdit = QLineEdit()
        self.maxFreqEdit = QLineEdit()

        box.addRow('Minimum frequency (Hz):',self.minFreqEdit)
        box.addRow('Maximum frequency (Hz):',self.maxFreqEdit)
        freqLimFrame.setLayout(box)

        optionLayout.addWidget(freqLimFrame)

        freqResFrame = QGroupBox('Frequency resolution')

        box = QFormLayout()

        self.filterEdit = QLineEdit()
        self.coeffEdit = QLineEdit()

        box.addRow('Number of filters:',self.filterEdit)
        box.addRow('Number of coefficients (MFCC only):',self.coeffEdit)
        freqResFrame.setLayout(box)

        optionLayout.addWidget(freqResFrame)

        #self.outputSimWidget = RadioSelectWidget('Output',
        #                                                {'Output as similarity (0 to 1)':True,
        #                                                'Output as distance':False})
        self.outputSimWidget = QCheckBox('Output as similarity (0 to 1)')

        optionLayout.addWidget(self.outputSimWidget)

        #self.multiprocessingWidget = RadioSelectWidget('Multiprocessing',
        #                                                {'Use multiprocessing':True,
        #                                                'Use single core':False})
        self.multiprocessingWidget = QCheckBox('Use multiprocessing')

        optionLayout.addWidget(self.multiprocessingWidget)

        optionFrame = QFrame()

        optionFrame.setLayout(optionLayout)

        aslayout.addWidget(optionFrame)

        asframe = QFrame()

        asframe.setLayout(aslayout)

        layout.addWidget(asframe)

        self.newTableButton = QPushButton('Calculate acoustic similarity\n(start new results table)')
        self.oldTableButton = QPushButton('Calculate acoustic similarity\n(add to current results table)')
        self.cancelButton = QPushButton('Cancel')
        self.aboutButton = QPushButton('About this function...')
        acLayout = QHBoxLayout()
        acLayout.addWidget(self.newTableButton)
        acLayout.addWidget(self.oldTableButton)
        acLayout.addWidget(self.cancelButton)
        acLayout.addWidget(self.aboutButton)
        self.newTableButton.clicked.connect(self.newTable)
        self.oldTableButton.clicked.connect(self.oldTable)
        self.aboutButton.clicked.connect(self.about)
        self.cancelButton.clicked.connect(self.reject)

        acFrame = QFrame()
        acFrame.setLayout(acLayout)

        layout.addWidget(acFrame)

        self.setLayout(layout)

        self.setWindowTitle('Acoustic similarity')

        self.thread = ASWorker()

    def calcAS(self):
        rep = self.representationWidget.value()
        alg = self.distAlgWidget.value()
        if self.filterEdit.text() in ['','0']:
            if rep == 'mfcc':
                self.filterEdit.setText('26')
            elif rep == 'envelopes':
                self.filterEdit.setText('8')
        if rep == 'mfcc' and self.coeffEdit.text() in ['','0']:
            self.coeffEdit.setText('12')
            if int(self.coeffEdit.text()) > int(self.filterEdit.text())-1:
                self.coeffEdit.setText(str(int(self.filterEdit.text())-1))
        if self.minFreqEdit.text() in ['']:
            self.minFreqEdit.setText('80')
        if self.maxFreqEdit.text() in ['']:
            self.maxFreqEdit.setText('7800')
        try:
            filters = int(self.filterEdit.text())
        except ValueError:
            return
        try:
            coeffs = int(self.coeffEdit.text())
        except ValueError:
            if rep == 'mfcc':
                return
        try:
            freq_lims = (float(self.minFreqEdit.text()),float(self.maxFreqEdit.text()))
        except ValueError:
            return
        kwargs = {
                'directory_one': self.directoryOne.value(),
                'directory_two': self.directoryTwo.value(),
                'rep':rep,
                'match_func':alg,
                'num_filters':filters,
                'num_coeffs':coeffs,
                'freq_lims':freq_lims,
                'output_sim':self.outputSimWidget.isChecked(),
                'use_multi':self.multiprocessingWidget.isChecked()}
        self.thread.setParams(kwargs)

        dialog = QProgressDialog('Calculating acoustic similarity...','Cancel',0,0)
        self.thread.dataReady.connect(self.setResults)
        self.thread.dataReady.connect(dialog.accept)

        self.thread.start()

        result = dialog.exec_()
        if result:
            self.accept()
        else:
            self.thread.terminate()


    def setResults(self,results):
        self.results = list()

        for r in results:
            self.results.append([os.path.split(self.directoryOne.value())[1],
                            os.path.split(self.directoryTwo.value())[1],
                            self.representationWidget.name(),
                            self.distAlgWidget.name(),
                            float(self.minFreqEdit.text()),
                            float(self.maxFreqEdit.text()),
                            int(self.filterEdit.text()),
                            int(self.coeffEdit.text()),
                            r,
                            self.outputSimWidget.isChecked()])

    def newTable(self):
        self.update = False
        self.calcAS()

    def oldTable(self):
        self.update = True
        self.calcAS()

    def about(self):
        pass
