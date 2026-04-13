import sys
import serial
import numpy as np
from scipy import signal
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore

class CustomAttentionMonitor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Attention")
        self.resize(800, 400)
        
        self.layout = QtWidgets.QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setYRange(0, 100)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot_widget)
        
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=5))
        
        self.fs = 64
        self.raw_buffer = [] 
        self.attention_history = [0] * 60
        
        COM_PORT = 'COM9'
        
        try:
            self.ser = serial.Serial(COM_PORT, 57600, timeout=0.01) 
        except Exception as e:
            print(f"포트 연결 에러: {e}")
            sys.exit()

        self.read_timer = QtCore.QTimer()
        self.read_timer.timeout.connect(self.read_serial)
        self.read_timer.start(20) 

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(1000) 

    def read_serial(self):
        new_data = []
        read_count = 0
        while self.ser.in_waiting and read_count < 1000:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    new_data.append(int(line))
                read_count += 1
            except:
                pass
                
        if new_data:
            self.raw_buffer.extend(new_data)
            if len(self.raw_buffer) > self.fs * 2:
                self.raw_buffer = self.raw_buffer[-self.fs * 2:]

    def calculate_attention(self, raw_data):
        data = np.array(raw_data)
        
        amplitude = np.max(data) - np.min(data)
        if amplitude < 20 or amplitude > 30000:
            return 0 
        
        data = data - np.mean(data)
        
        freqs, psd = signal.welch(data, fs=self.fs, nperseg=len(data))
        
        idx_alpha = np.logical_and(freqs >= 8, freqs <= 12)
        idx_beta = np.logical_and(freqs >= 13, freqs <= 30)
        
        mean_power_alpha = np.mean(psd[idx_alpha])
        mean_power_beta = np.mean(psd[idx_beta])
        
        ratio = mean_power_beta / (mean_power_alpha + 1e-6)
        
        if ratio > 0.08:
            return 0
        
        min_ratio = 0.025
        max_ratio = 0.06
        
        attention_score = (ratio - min_ratio) / (max_ratio - min_ratio) * 100
        
        attention_score = max(0, min(100, attention_score))
        
        print(f"Amplitude: {amplitude:<5.0f} | Beta/Alpha ratio: {ratio:<4.2f} => Attention score: {attention_score:.0f}")
        return attention_score

    def update_plot(self):
        if len(self.raw_buffer) >= self.fs:
            data_for_calc = self.raw_buffer[-self.fs:]
            
            calc_attention = self.calculate_attention(data_for_calc)
            
            self.attention_history.append(calc_attention)
            self.attention_history = self.attention_history[-60:]
            
            self.curve.setData(self.attention_history)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = CustomAttentionMonitor()
    window.show()
    sys.exit(app.exec())