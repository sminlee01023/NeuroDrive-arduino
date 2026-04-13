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
        self.plot_widget.setYRange(0, 100) # 집중도 점수 0~100
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot_widget)
        
        # 집중도 그래프 라인 (파란색, 두껍게)
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=5))
        
        self.fs = 64 # 샘플링 주파수
        self.raw_buffer = [] 
        self.attention_history = [0] * 60 # 60초 분량 화면 표시
        
        COM_PORT = 'COM9' # 🌟 본인의 ESP32 포트 번호로 꼭 변경하세요!
        
        try:
            self.ser = serial.Serial(COM_PORT, 57600, timeout=0.01) 
        except Exception as e:
            print(f"포트 연결 에러: {e}")
            sys.exit()

        # ⏱️ 타이머 1: 시리얼 데이터 수신용 (매우 빠르게 뒤에서 버퍼만 채움)
        self.read_timer = QtCore.QTimer()
        self.read_timer.timeout.connect(self.read_serial)
        self.read_timer.start(20) 

        # ⏱️ 타이머 2: 집중도 계산 및 화면 갱신용 (정확히 1초(1000ms)마다 실행!)
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_timer.start(1000) 

    def read_serial(self):
        """데이터를 읽어서 버퍼에 쌓아두기만 하는 함수"""
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
            # 메모리 폭주 방지: 버퍼에 최대 최근 2초(1024개) 분량만 남김
            if len(self.raw_buffer) > self.fs * 2:
                self.raw_buffer = self.raw_buffer[-self.fs * 2:]

    def calculate_attention(self, raw_data):
        """원시 데이터로 집중도 계산 (노이즈 필터 포함)"""
        data = np.array(raw_data)
        
        # 🌟 노이즈 필터: 데이터의 진폭(최댓값 - 최솟값)을 확인
        # 피부에서 떨어져서 신호가 0에 가깝거나(20 미만), 노이즈가 껴서 폭주하면(2000 초과) 집중도 0점 처리
        amplitude = np.max(data) - np.min(data)
        if amplitude < 20 or amplitude > 30000:
            return 0 
        
        # 직류 성분 제거
        data = data - np.mean(data)
        
        # 주파수 분석 (FFT)
        freqs, psd = signal.welch(data, fs=self.fs, nperseg=len(data))
        
        idx_alpha = np.logical_and(freqs >= 8, freqs <= 12)
        idx_beta = np.logical_and(freqs >= 13, freqs <= 30)
        
        # 🌟 합산(sum) 대신 평균(mean)을 사용하여 대역폭 넓이 차이로 인한 오류 방지
        mean_power_alpha = np.mean(psd[idx_alpha])
        mean_power_beta = np.mean(psd[idx_beta])
        
        # 베타/알파 비율
        ratio = mean_power_beta / (mean_power_alpha + 1e-6)
        
        if ratio > 0.08:
            return 0
        
        min_ratio = 0.025
        max_ratio = 0.06
        
        attention_score = (ratio - min_ratio) / (max_ratio - min_ratio) * 100
        
        # 0 ~ 100 사이로 값 가두기
        attention_score = max(0, min(100, attention_score))
        
        print(f"진폭: {amplitude:<5.0f} | Beta/Alpha비율: {ratio:<4.2f} => 무제한 점수: {attention_score:.0f}점")
        return attention_score

    def update_plot(self):
        """정확히 1초마다 실행되어 그래프를 한 칸씩 그리는 함수"""
        # 버퍼에 최소 1초(512개) 분량의 데이터가 있는지 확인
        if len(self.raw_buffer) >= self.fs:
            # 가장 최근 1초(512개) 분량의 데이터만 싹둑 잘라서 가져옴
            data_for_calc = self.raw_buffer[-self.fs:]
            
            # 계산 수행
            calc_attention = self.calculate_attention(data_for_calc)
            
            # 리스트에 추가 및 화면 스크롤 유지
            self.attention_history.append(calc_attention)
            self.attention_history = self.attention_history[-60:]
            
            # 그래프 그리기
            self.curve.setData(self.attention_history)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = CustomAttentionMonitor()
    window.show()
    sys.exit(app.exec())