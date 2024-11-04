import sys
import random
import requests
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QTabWidget, QProgressBar, QGroupBox, QFrame, 
                            QPushButton, QScrollArea, QMessageBox, QComboBox, QSlider,
                            QListWidget, QListWidgetItem, QGridLayout)  # 添加 QGridLayout
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, QRect, QSize  # 移除 QCloseEvent
from PyQt5.QtGui import QFont, QColor, QPalette
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import logging
import serial
import threading

# 设置matplotlib的后端为Qt5Agg
matplotlib.use('Qt5Agg')

# 常量定义
REFRESH_INTERVAL = 5000  # 刷新间隔（毫秒）
DEFAULT_WINDOW_SIZE = (1280, 800)
DEFAULT_FONT_FAMILY = "Microsoft YaHei"
DEFAULT_CHINESE_FONT = "方正清刻本悦宋简体"  # 中体
DEFAULT_ENGLISH_FONT = "Century Gothic"    # 英文字体

# 颜色常量
COLORS = {
    'wind': '#4CAF50',    # 绿色
    'solar': '#FFC107',   # 黄色
    'water': '#2196F3',   # 蓝色
    'background': '#f5f6fa',
    'warning': '#ff6b6b',
    'success': '#27ae60'
}

# 辅助函数
def format_power(value):
    """格式化能源数值"""
    if value >= 1000:
        return f"{value/1000:.1f}MW"
    return f"{value:.1f}kW"

def get_time_range(hours=24):
    """获取时间范围"""
    current = datetime.now()
    return [current + timedelta(hours=i) for i in range(hours)]

class WeatherPredictor:
    """天气预测类"""
    def __init__(self):
        self.API_KEY = '2a35c4afdc5763352253d11d40261a85'  
        self.latitude = 29.0781  
        self.longitude = 119.6476  
        
        # 设置matplotlib中文支持
        rcParams['font.sans-serif'] = ['SimHei']
        rcParams['axes.unicode_minus'] = False
        
        self.max_retries = 3
        self.retry_delay = 1  
    
    def get_current_weather(self):
        """获取当前天气数据（带重试机制）"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.build_api_url(), timeout=10)
                response.raise_for_status()
                return self.parse_weather_data(response.json())
            except requests.exceptions.RequestException as e:
                print(f"获取天气数据失败: {e}, 尝试次数: {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(self.retry_delay)
        return None

    def build_api_url(self):
        """构建API URL"""
        return f"http://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.API_KEY}&units=metric&lang=zh_cn"

    def parse_weather_data(self, data):
        """解析天气数据"""
        try:
            return {
                'temperature': data['main']['temp'],
                'wind_speed': data['wind']['speed'],
                'cloud_coverage': data['clouds']['all'],
                'sunlight': 100 - data['clouds']['all'],  
                'weather_description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure']
            }
        except KeyError as e:
            print(f"解析天气数据错误: {e}")
            return None

    def predict_weather(self, hours_ahead=24):
        """预测未来天气"""
        current_weather = self.get_current_weather()
        if not current_weather:
            return self._generate_mock_predictions(hours_ahead)
            
        predictions = []
        current_hour = datetime.now()
        
        for i in range(hours_ahead):
            prediction = {
                'time': current_hour + timedelta(hours=i),
                'weather': current_weather['weather_description'],
                'wind_speed': current_weather['wind_speed'] * random.uniform(0.8, 1.2),
                'solar_intensity': current_weather['sunlight'] * random.uniform(0.7, 1.3),
                'rainfall': current_weather['humidity'] * random.uniform(0.1, 0.3)
            }
            predictions.append(prediction)
        
        return predictions
    
    def _generate_mock_predictions(self, hours_ahead):
        """生成模拟预测数据（当API不可用时使用）"""
        predictions = []
        current_hour = datetime.now()
        
        weather_patterns = {
            'sunny': {'wind': (10, 30), 'solar': (60, 100), 'rain': (0, 10)},
            'cloudy': {'wind': (20, 50), 'solar': (30, 60), 'rain': (20, 40)},
            'rainy': {'wind': (40, 70), 'solar': (10, 30), 'rain': (60, 100)}
        }       
        
        for i in range(hours_ahead):
            weather_type = random.choice(list(weather_patterns.keys()))
            pattern = weather_patterns[weather_type]
            prediction = {
                'time': current_hour + timedelta(hours=i),
                'weather': weather_type,
                'wind_speed': random.uniform(*pattern['wind']),
                'solar_intensity': random.uniform(*pattern['solar']),
                'rainfall': random.uniform(*pattern['rain'])
            }
            predictions.append(prediction)
        
        return predictions

    def get_daily_forecast(self):
        """获取每日天气预报"""
        try:
            # 使用 OpenWeather API 的 5 day / 3 hour forecast 接口
            url = f"http://api.openweathermap.org/data/2.5/forecast?lat={self.latitude}&lon={self.longitude}&appid={self.API_KEY}&units=metric&lang=zh_cn"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 处理预报数据
            forecast = []
            current_date = None
            daily_data = {}
            
            for item in data['list']:
                date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                
                if current_date != date:
                    if current_date is not None:
                        forecast.append(daily_data)
                    current_date = date
                    daily_data = {
                        'date': date,
                        'temp_min': item['main']['temp_min'],
                        'temp_max': item['main']['temp_max'],
                        'weather': item['weather'][0]['description'],
                        'wind_speed': item['wind']['speed'],
                        'humidity': item['main']['humidity']
                    }
                else:
                    # 更新当天的最高最低温度
                    daily_data['temp_min'] = min(daily_data['temp_min'], item['main']['temp_min'])
                    daily_data['temp_max'] = max(daily_data['temp_max'], item['main']['temp_max'])
            
            # 添加最后一天的数据
            if daily_data:
                forecast.append(daily_data)
            
            return forecast[:7]  # 返回最多7天的预报
            
        except Exception as e:
            print(f"获取天气预报错误: {e}")
            return None

class EnergyStorage:
    """能源存储管理类"""
    def __init__(self):
        self.battery_capacity = 1000  # 1000kWh总容量
        self.current_storage = 500    # 当前储能
        self.ev_charging = False      # 电动车充电状态
        self.ev_battery_level = 50    # 电动车电量水平
        self.charging_history = []    # 充电历史记录
        self.discharge_history = []   # 放电历史记录

    def store_energy(self, amount):
        """储存能源"""
        available_space = self.battery_capacity - self.current_storage
        storable_amount = min(amount, available_space)
        self.current_storage += storable_amount
        
        if storable_amount > 0:
            self.charging_history.append({
                'amount': storable_amount,
                'time': datetime.now()
            })
        
        return storable_amount

    def use_energy(self, amount):
        """使用储存的能源"""
        available_energy = min(amount, self.current_storage)
        self.current_storage -= available_energy
        
        if available_energy > 0:
            self.discharge_history.append({
                'amount': available_energy,
                'time': datetime.now()
            })
        
        return available_energy

    def get_storage_status(self):
        """获取储能系统状态"""
        return {
            'current_storage': self.current_storage,
            'capacity': self.battery_capacity,
            'percentage': (self.current_storage / self.battery_capacity) * 100,
            'ev_charging': self.ev_charging,
            'ev_battery_level': self.ev_battery_level
        }

    def optimize_charging_schedule(self, predicted_energy_surplus):
        """优化充电计划"""
        best_charging_periods = []
        current_hour = datetime.now().hour
        
        for hour, surplus in enumerate(predicted_energy_surplus):
            actual_hour = (current_hour + hour) % 24
            if surplus > 30 and 10 <= actual_hour <= 16:
                best_charging_periods.append({
                    'hour': actual_hour,
                    'surplus': surplus
                })
        
        return best_charging_periods

class EnergyManager:
    """能源管理核心类"""
    def __init__(self, dashboard=None):
        self.dashboard = dashboard
        self.wind_energy = 0
        self.solar_energy = 0
        self.water_energy = 0
        self.total_energy = 0
        self.water_level = 50
        self.weather_predictor = WeatherPredictor()
        self.energy_history = []
        self.predictions = []
        self.storage = EnergyStorage()
        self.energy_priority = {
            'wind': 1,
            'solar': 2,
            'water': 3
        }
        self.current_energy = {
            'wind': 0,
            'solar': 0,
            'water': 0,
            'total': 0
        }
        self.storage_status = {
            'battery_level': 50,
            'charging': False,
            'efficiency': 85,
            'ev_status': '未连接',
            'last_charge': None
        }
        self.water_system = {
            'water_level': 70,
            'pump_status': 'off',
            'flow_rate': 0,
            'power_output': 0,
            'collection_rate': 0
        }
        self.system_status = "正常运行"
        self.last_update = None
        self.alerts = []
        self.maintenance_schedule = []
        self.logger = self.setup_logger()
        self.fan_count = 0  # 添加风扇数量属性
        self.serial_manager = SERIAL_MANAGER  # 使用全局串口管理器

    def setup_logger(self):
        """置日志记录器"""
        logger = logging.getLogger('EnergyManager')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger

    def update_energy_data(self):
        """更新能源数据"""
        try:
            # 获取风扇数量对应的风能
            wind_power = self.serial_manager.fan_count * 20  # 使用 serial_manager
            
            # 获取水泵发电量
            water_power = self.serial_manager.get_water_power()  # 使用 serial_manager
            
            # 更新能源数据
            self.current_energy.update({
                'wind': wind_power,
                'solar': 0,  # 太阳能保持为0
                'water': water_power,
                'total': wind_power + water_power
            })
            
            # 通过仪盘更新显示
            if self.dashboard:
                # 更新各能源显示
                self.dashboard.update_energy_display(self.current_energy)
                
        except Exception as e:
            print(f"更新能源数据错误: {e}")

    def predict_energy(self):
        """测未来能源供应情况"""
        weather_predictions = self.weather_predictor.predict_weather()
        self.predictions = []
        
        for pred in weather_predictions:
            # 基于实际天气数据优化能源转换系数
            wind_coefficient = 0.8 if pred['wind_speed'] > 5 else 0.5
            solar_coefficient = 1.2 if pred['solar_intensity'] > 70 else 0.8
            water_coefficient = 0.5 if pred['rainfall'] > 50 else 0.3
            
            energy_pred = {
                'time': pred['time'],
                'wind_energy': pred['wind_speed'] * wind_coefficient,
                'solar_energy': pred['solar_intensity'] * solar_coefficient,
                'water_energy': pred['rainfall'] * water_coefficient
            }
            self.predictions.append(energy_pred)
            
        return self.predictions

    def check_system_status(self):
        """检查系统状态并生成警报"""
        current_time = datetime.now()
        
        # 检查更新时间
        if self.last_update and (current_time - self.last_update).seconds > 300:
            self.alerts.append({
                'level': 'warning',
                'message': '数据更新延迟超过5分钟',
                'time': current_time
            })
            
        # 检查水箱水位
        if self.water_system['water_level'] < 30:
            self.alerts.append({
                'level': 'warning',
                'message': '水箱水位低于30%',
                'time': current_time
            })
            
        # 检查能源产出
        if self.current_energy['total'] < 100:
            self.alerts.append({
                'level': 'warning',
                'message': '总能源产出低于100kW',
                'time': current_time
            })
            
        # 检查储能效率
        if self.storage_status['efficiency'] < 75:
            self.alerts.append({
                'level': 'warning',
                'message': '储能效率低于75%',
                'time': current_time
            })
            
        # 检查各能源系统
        for energy_type, value in self.current_energy.items():
            if energy_type != 'total' and value < 30:
                self.alerts.append({
                    'level': 'warning',
                    'message': f'{energy_type}能源产出低于30kW',
                    'time': current_time
                })
                
        # 保持最近50条警报
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]

    def get_optimization_suggestions(self):
        """"""
        suggestions = []
        stats = self.get_efficiency_stats()
        
        # 基于效率统计生成建议
        if stats['storage_efficiency'] < 80:
            suggestions.append({
                'type': 'storage',
                'message': "建议检查储能系统，当前率较低",
                'priority': 'high'
            })
            
        if stats['conversion_rate'] < 80:
            suggestions.append({
                'type': 'conversion',
                'message': "能源转换效率低于80%，建议查转换设备",
                'priority': 'medium'
            })
            
        if stats['utilization_rate'] < 70:
            suggestions.append({
                'type': 'utilization',
                'message': "设备利用率低于70%，建议优化设备使用计划",
                'priority': 'medium'
            })
            
        # 基于能源状态生成建议
        for energy_type, value in self.current_energy.items():
            if energy_type != 'total':
                if value < 40:
                    suggestions.append({
                        'type': energy_type,
                        'message': f"{energy_type}系统产出低，建议检查相关设备",
                        'priority': 'high' if value < 30 else 'medium'
                    })
                    
        return suggestions

    def get_weekly_prediction(self):
        """获取周预测数据"""
        try:
            weekly_data = []
            for i in range(7):  # 生成7天的预测数据
                data = {
                    'date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
                    'wind': random.uniform(30, 100),
                    'solar': random.uniform(20, 80),
                    'water': random.uniform(10, 60)
                }
                weekly_data.append(data)
            return weekly_data
        except Exception as e:
            print(f"获取周预测数据错误: {e}")
            return None

    def check_maintenance(self):
        """检查设备维护计划"""
        current_time = datetime.now()
        due_maintenance = []
        
        for equipment in self.maintenance_schedule:
            if current_time >= equipment['next_maintenance']:
                due_maintenance.append({
                    'equipment': equipment['name'],
                    'last_maintenance': equipment['last_maintenance'],
                    'priority': equipment['priority']
                })
        return due_maintenance

class EnergyWidget(QFrame):
    """能源显示组件"""
    def __init__(self, energy_type, color, font_family):
        super().__init__()
        self.energy_type = energy_type
        self.color = color
        self.font_family = font_family
        self.init_ui()

    def init_ui(self):
        # 设置基本属性
        self.setMinimumWidth(380)
        self.setMaximumWidth(480)
        self.setMinimumHeight(300)
        
        # 设置圆角卡片式，移除阴影，优化渐变
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba({self.get_lighter_color_rgb()}));
                border-radius: 25px;
                padding: 25px;
            }}
            QLabel#typeLabel {{
                color: {self.color};
                font-size: 28px;
                font-weight: bold;
                margin: 5px 0;
                padding: 5px 0;
                background: transparent;
            }}
            QLabel#valueLabel {{
                color: {self.color};
                font-size: 48px;
                font-weight: bold;
                margin: 10px 0;
                padding: 10px 0;
                min-height: 70px;
                background: transparent;
            }}
            QLabel#statusLabel {{
                color: #666666;
                font-size: 18px;
                margin: 5px 0;
                padding: 5px 0;
                min-height: 30px;
                background: transparent;
            }}
            QProgressBar {{
                background-color: rgba(240, 240, 240, 150);
                border: none;
                height: 8px;
                border-radius: 4px;
                margin: 15px 0;
            }}
            QProgressBar::chunk {{
                background: {self.color};
                border-radius: 4px;
            }}
        """)

        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(25)  # 增加整体间距
        layout.setContentsMargins(25, 25, 25, 25)

        # 能源类型标签
        type_label = QLabel(self.energy_type)
        type_label.setObjectName("typeLabel")
        type_label.setFont(QFont(DEFAULT_CHINESE_FONT, 28, QFont.Bold))
        type_label.setAlignment(Qt.AlignLeft)
        type_label.setFixedHeight(45)
        layout.addWidget(type_label)

        # 创建数值显示区域
        self.value_label = QLabel("0 kW")
        self.value_label.setObjectName("valueLabel")
        self.value_label.setFont(QFont(DEFAULT_ENGLISH_FONT, 48, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setFixedHeight(80)
        self.value_label.setContentsMargins(0, 0, 0, 20)  # 增加底部边距
        layout.addWidget(self.value_label)

        # 添加一个占位的空白区域
        spacer = QWidget()
        spacer.setFixedHeight(10)  # 添加固定高度的空白
        layout.addWidget(spacer)

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setContentsMargins(0, 10, 0, 10)  # 增加上下边距
        layout.addWidget(self.progress_bar)

        # 状态文本
        self.status_label = QLabel("运行状: 正常")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.status_label.setAlignment(Qt.AlignRight)
        self.status_label.setFixedHeight(35)
        layout.addWidget(self.status_label)

        # 设置布局的拉伸因子
        layout.setStretchFactor(type_label, 2)
        layout.setStretchFactor(self.value_label, 4)
        layout.setStretchFactor(spacer, 1)
        layout.setStretchFactor(self.progress_bar, 1)
        layout.setStretchFactor(self.status_label, 2)

    def get_lighter_color_rgb(self):
        """获取渐变色的浅色端（RGB格式）"""
        color = QColor(self.color)
        h, s, v, a = color.getHsv()
        color.setHsv(h, int(s * 0.1), min(255, int(v * 1.3)), 20)  # 降低alpha值使渐变更柔和
        return f"{color.red()}, {color.green()}, {color.blue()}, {color.alpha()}"

    def get_lighter_color(self):
        """获取变色的浅色端"""
        color = QColor(self.color)
        h, s, v, a = color.getHsv()
        color.setHsv(h, int(s * 0.1), min(255, int(v * 1.3)), 20)  # 低alpha值使渐变更柔和
        return color.name()

    def update_value(self, value):
        """更新显示的值"""
        # 更新数值
        self.value_label.setText(f"{value:.1f} kW")
        
        # 更新进度条
        self.progress_bar.setValue(int(min(value, 100)))
        
        # 更状态
        if value > 80:
            status = "高效运行"
            status_color = "#4CAF50"  # 绿色
        elif value > 40:
            status = "正常运行"
            status_color = "#2196F3"  # 蓝色
        else:
            status = "低效运行"
            status_color = "#FFC107"  # 黄色
            
        self.status_label.setText(f"运行状态: {status}")
        self.status_label.setStyleSheet(f"color: {status_color};")





class StorageWidget(QFrame):
    """储能显示组件"""
    def __init__(self, font_family):
        super().__init__()
        self.font_family = font_family
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
            QLabel {
                min-height: 35px;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 储能状态标签
        self.storage_label = QLabel("储能系统状态")
        self.storage_label.setFont(QFont(DEFAULT_CHINESE_FONT, 14, QFont.Bold))
        self.storage_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.storage_label)

        # 储能进度条
        self.storage_progress = QProgressBar()
        self.storage_progress.setMinimumHeight(25)
        self.storage_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 4px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
            }
        """)
        layout.addWidget(self.storage_progress)
        
        # 电动车状态标签
        self.ev_status = QLabel("能量驿站充电桩状态正常")  
        self.ev_status.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.ev_status.setStyleSheet("color: #666666;")
        self.ev_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ev_status)

        # 风扇控制按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        for i in range(4):
            btn = QPushButton(f"启用{i}个风扇")
            btn.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
            btn.clicked.connect(lambda checked, count=i: (
                self.serial_manager.send_command(f"FAN{count}"),
                self.update_fan_status(count)  # 确保调用更新风扇状态的方法
            ))  
            button_layout.addWidget(btn)
        layout.addLayout(button_layout)

    def update_storage_status(self, status):
        """更新储能状态"""
        try:
            
            self.storage_progress.setValue(int(status['percentage']))
            self.battery_value.setText(f"{status['percentage']}%")
            
            # 更新电动车状态
            if status['ev_charging']:
                self.ev_status_label.setText("充电中")
                self.ev_status_label.setStyleSheet("color: #4CAF50;")
            else:
                self.ev_status_label.setText("未连接")
                self.ev_status_label.setStyleSheet("color: #666666;")
            
            self.ev_progress.setValue(status['ev_battery_level'])
            
            # 更新风扇状态
            running_fans = status.get('running_fans', 3)  # 默认所有风扇运行
            total_fans = 3
            
            # 更新总体状态
            self.fan_status_label.setText(f"{running_fans}/{total_fans} 风扇正运行")
            if running_fans == total_fans:
                self.fan_status_label.setStyleSheet("color: #4CAF50;")  # 绿色
            elif running_fans > 0:
                self.fan_status_label.setStyleSheet("color: #FFC107;")  # 黄色
            else:
                self.fan_status_label.setStyleSheet("color: #F44336;")  # 红色
        except Exception as e:
            print(f"更新储能状态错误: {e}")

    def update_fan_status(self, count):
        """更新风扇状态显示"""
        if 0 <= count <= 3:
            self.fan_status_label.setText(f"风扇运行状态正常")
            if count == 3:
                self.fan_status_label.setStyleSheet("color: #4CAF50;")  # 绿色
            elif count > 0:
                self.fan_status_label.setStyleSheet("color: #FFC107;")  # 黄色
            else:
                self.fan_status_label.setStyleSheet("color: #F44336;")  # 红色

class PredictionWidget(QFrame):
    """预测显示组"""
    def __init__(self, font_family):
        super().__init__()
        self.font_family = font_family
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建图表
        fig = Figure(figsize=(12, 4), facecolor='#313244')
        self.canvas = FigureCanvas(fig)
        self.ax = fig.add_subplot(111)
        
        # 设图表样式
        self.ax.set_facecolor('#313244')
        fig.patch.set_facecolor('#313244')
        self.ax.tick_params(colors='#cdd6f4')
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')
        self.ax.grid(True, linestyle='--', alpha=0.3, color='#45475a')
        
        layout.addWidget(self.canvas)

    def update_prediction(self, predictions, colors):
        """更新预测图"""
        self.ax.clear()
        
        times = [pred['time'].strftime('%H:00') for pred in predictions]
        wind_data = [pred['wind_energy'] for pred in predictions]
        solar_data = [pred['solar_energy'] for pred in predictions]
        water_data = [pred['water_energy'] for pred in predictions]
        
        # 使用更新的颜色方案
        self.ax.plot(times, wind_data, label='风能', color='#89b4fa', linewidth=2)
        self.ax.plot(times, solar_data, label='太能', color='#fab387', linewidth=2)
        self.ax.plot(times, water_data, label='水能', color='#94e2d5', linewidth=2)
        
        self.ax.set_xlabel('预测时间', color='#cdd6f4')
        self.ax.set_ylabel('预计功率 (kW)', color='#cdd6f4')
        self.ax.set_title('24小时能源预测', color='#cdd6f4', pad=20)
        self.ax.legend(facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4')
        self.ax.grid(True, linestyle='--', alpha=0.3, color='#45475a')
        
        # 设置刻度标签颜
        self.ax.tick_params(colors='#cdd6f4')
        
        plt.xticks(rotation=45)
        self.canvas.draw()



class AdviceWidget(QFrame):
    """建议显示组件"""
    def __init__(self, font_family):
        super().__init__()
        self.font_family = font_family
        self.fonts = {
            'title': {'family': font_family, 'size': 14, 'weight': QFont.Bold},
            'content': {'family': font_family, 'size': 12, 'weight': QFont.Normal}
        }
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                margin: 8px;
            }
            QLabel {
                color: #2c3e50;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # 题
        title = QLabel("能源使用建议")
        title_font = QFont(
            self.fonts['title']['family'],
            self.fonts['title']['size'],
            self.fonts['title']['weight']
        )  # 添加右括号
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 建议内容
        self.advice_list = QLabel()
        self.advice_list.setWordWrap(True)
        content_font = QFont(
            self.fonts['content']['family'],
            self.fonts['content']['size'],
            self.fonts['content']['weight']
        )  
        self.advice_list.setFont(content_font)
        layout.addWidget(self.advice_list)

    def update_advice(self, suggestions):
        """更新建议内容"""
        if not suggestions:
            self.advice_list.setText("暂无建议")
            return
            
        advice_text = "\n".join([f"• {suggestion['message']}" for suggestion in suggestions])
        self.advice_list.setText(advice_text)

class EnergyDashboard(QMainWindow):
    """能源理系统主窗口"""
    def __init__(self):
        super().__init__()
        
        # 定义颜色方案
        self.colors = {
            'wind': '#4CAF50',    # 绿色
            'solar': '#FFC107',   # 黄色
            'water': '#2196F3',   # 蓝色
            'background': '#f5f6fa',
            'warning': '#ff6b6b',
            'success': '#27ae60'
        }
        
        # 使用全局串口管理器
        self.serial_manager = SERIAL_MANAGER
        self.serial_manager.dashboard = self
        if not self.serial_manager.is_connected:
            self.serial_manager.connect()
        
        # 创建能源管理器
        self.energy_manager = EnergyManager(self)
        
        # 创建天气预测器
        self.weather_predictor = WeatherPredictor()  # 添加这行
        
        # 初始化UI
        self.init_ui()
        
        # 启动定时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # 每秒更新一次
        
        self.is_updating = False
        self.last_update_time = None
        self.error_count = 0

        # 添加AI调整定时器
        self.ai_timer = QTimer()
        self.ai_timer.setInterval(3000)  # 每3秒调整一次
        self.ai_timer.timeout.connect(self.update_ai_priority)
        
        # 初始化电动车充电状态
        self.ev_battery_level = random.randint(20, 80)  # 随机初始电量
        self.ev_charging_start_time = None
        
        # 初始化风扇状态
        self.fan_count = 0  # 初始时所有风扇关闭
        self.serial_manager.control_fans(0)  # 发送关闭风扇命令

        # 创建储能标签页并保存引用
        self.storage_tab = self.create_storage_tab()

    def init_ui(self):
        """初始化用户界面"""
        # 获取所有屏幕
        screens = QApplication.screens()
        
        # 如果有副屏，使用副屏
        if len(screens) > 1:
            screen = screens[1]  # 副屏
        else:
            screen = screens[0]  # 主屏
        
        # 获取副屏几何信息和DPI
        screen_geometry = screen.geometry()
        screen_dpi = screen.physicalDotsPerInch()
        
        # 增加缩放因子
        scale_factor = screen_dpi / 96.0 * 1.3  # 增加30%的缩放
        
        # 调整基字体大小
        base_font_size = int(12 * scale_factor)
        self.title_font_cn = QFont(DEFAULT_CHINESE_FONT, int(48 * scale_factor), QFont.Bold)  # 增大标题字体
        self.title_font_en = QFont(DEFAULT_ENGLISH_FONT, int(36 * scale_factor), QFont.Bold)  # 增大英文标题字体
        self.subtitle_font = QFont(DEFAULT_CHINESE_FONT, int(28 * scale_factor))  # 增大副标题字体
        self.normal_font = QFont(DEFAULT_CHINESE_FONT, int(20 * scale_factor))  # 增大正常文字字体
        
        # 设置窗口标题和位置
        self.setWindowTitle('智维清域 - Pure-flow Fusion Dynamics')
        self.move(screen_geometry.x(), screen_geometry.y())
        self.setGeometry(screen_geometry)
        
        # 设置窗口最小尺寸
        min_width = int(1024 * scale_factor)
        min_height = int(768 * scale_factor)
        self.setMinimumSize(min_width, min_height)
        
        # 设置窗口最大化
        self.showMaximized()
        
        # 创建央件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建标题区域
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setSpacing(5)  # 减小标题间距
        title_layout.setContentsMargins(50, 15, 50, 15)  # 减小上下边距
        
        # 中文标题
        title_cn = QLabel('智维清域')
        title_cn.setFont(QFont(DEFAULT_CHINESE_FONT, 42, QFont.Bold))
        title_cn.setStyleSheet("""
            color: #1a237e;
            padding: 5px 0px;
        """)
        title_cn.setAlignment(Qt.AlignLeft)
        
        # 英文标题
        title_en = QLabel('Pure-flow Fusion Dynamics')
        title_en.setFont(QFont(DEFAULT_ENGLISH_FONT, 32, QFont.Bold))
        title_en.setStyleSheet("""
            color: #1976D2;
            padding: 3px 0px;
        """)
        title_en.setAlignment(Qt.AlignLeft)
        
        # 副标题
        subtitle = QLabel('AI赋能的全景清洁能源管理平台')
        subtitle.setFont(QFont(DEFAULT_CHINESE_FONT, 24))
        subtitle.setStyleSheet("""
            color: #2196F3;
            padding: 3px 0px;
        """)
        subtitle.setAlignment(Qt.AlignRight)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            background-color: #E3F2FD;
            height: 2px;
            margin: 5px 0px;
        """)
        
        # 添加标题到布局
        title_layout.addWidget(title_cn)
        title_layout.addWidget(title_en)
        title_layout.addWidget(subtitle)
        title_layout.addWidget(separator)
        
        # 添加标题区域到主布局
        main_layout.addWidget(title_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        tab_widget.setFont(QFont(DEFAULT_CHINESE_FONT, 14))  # 减小标签页字体大小
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin: 0px 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E3F2FD, stop:1 #BBDEFB);
                color: #1976D2;
            }
            QTabBar::tab:!selected {
                background: #F5F5F5;
                color: #666666;
            }
            QTabBar::tab:hover {
                background: #E3F2FD;
            }
        """)
        
        # 添加主页标签
        main_tab = self.create_main_tab()
        tab_widget.addTab(main_tab, "主页")
        
        # 添加预测标签
        prediction_tab = self.create_prediction_tab()
        tab_widget.addTab(prediction_tab, "能源预测")
        
        # 添加储能标签
        storage_tab = self.create_storage_tab()
        tab_widget.addTab(storage_tab, "储能系统")
        
        # 添加优先级标签
        priority_tab = self.create_priority_tab()
        tab_widget.addTab(priority_tab, "能源优先级")
        
        # 添加天气预报标签
        weather_tab = self.create_weather_tab()
        tab_widget.addTab(weather_tab, "天气预报")
        
        main_layout.addWidget(tab_widget)

    def create_main_tab(self):
        """创建主页标签"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建顶部信息区域
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setSpacing(15)
        
        # 创建总能源信息卡片
        total_energy_card = QFrame()
        total_energy_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E3F2FD);
                border-radius: 20px;
                padding: 20px;
            }
            QLabel {
                color: #333333;
                background: transparent;
            }
        """)
        total_energy_layout = QVBoxLayout(total_energy_card)
        
        total_label = QLabel("总能源产出")
        total_label.setFont(QFont(DEFAULT_CHINESE_FONT, 18, QFont.Bold))
        total_label.setStyleSheet("color: #1976D2;")
        total_label.setAlignment(Qt.AlignCenter)
        
        self.total_energy_value = QLabel("0 kW")
        self.total_energy_value.setFont(QFont(DEFAULT_ENGLISH_FONT, 24, QFont.Bold))
        self.total_energy_value.setStyleSheet("color: #2196F3;")
        self.total_energy_value.setAlignment(Qt.AlignCenter)
        
        total_energy_layout.addWidget(total_label)
        total_energy_layout.addWidget(self.total_energy_value)
        
        # 创建能源占比卡片
        ratio_card = QFrame()
        ratio_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E8F5E9);
                border-radius: 20px;
                padding: 20px;
            }
            QLabel {
                color: #333333;
                background: transparent;
            }
        """)
        ratio_layout = QVBoxLayout(ratio_card)
        
        ratio_label = QLabel("能源占比")
        ratio_label.setFont(QFont(DEFAULT_CHINESE_FONT, 18, QFont.Bold))
        ratio_label.setStyleSheet("color: #2E7D32;")
        ratio_label.setAlignment(Qt.AlignCenter)
        
        self.ratio_value = QLabel("风能: 0% | 太阳能: 0% | 水能: 0%")
        self.ratio_value.setFont(QFont(DEFAULT_ENGLISH_FONT, 16))
        self.ratio_value.setStyleSheet("color: #4CAF50;")
        self.ratio_value.setAlignment(Qt.AlignCenter)
        
        ratio_layout.addWidget(ratio_label)
        ratio_layout.addWidget(self.ratio_value)
        
        # 创建当前主要产出能源卡片
        main_energy_card = QFrame()
        main_energy_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #FFF3E0);
                border-radius: 20px;
                padding: 20px;
            }
            QLabel {
                color: #333333;
                background: transparent;
            }
        """)
        main_energy_layout = QVBoxLayout(main_energy_card)
        
        main_title = QLabel("当前主要产出能源")
        main_title.setFont(QFont(DEFAULT_CHINESE_FONT, 18, QFont.Bold))
        main_title.setStyleSheet("color: #E65100;")
        main_title.setAlignment(Qt.AlignCenter)
        main_energy_layout.addWidget(main_title)
        
        self.main_energy_label = QLabel("风能")
        self.main_energy_label.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        self.main_energy_label.setStyleSheet("color: #FF9800;")
        self.main_energy_label.setAlignment(Qt.AlignCenter)
        main_energy_layout.addWidget(self.main_energy_label)
        
        # 添加到顶部布局
        top_layout.addWidget(total_energy_card, 1)  # 比例1
        top_layout.addWidget(ratio_card, 2)         # 比例2
        top_layout.addWidget(main_energy_card, 1)   # 比例1
        
        # 添加顶部区域到主布局
        layout.addWidget(top_widget)
        
        # 创建能源显示区域
        energy_group = QGroupBox("实时能源数据")  
        energy_group.setFont(QFont(DEFAULT_CHINESE_FONT, 20, QFont.Bold))
        energy_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e0e0e0;
                border-radius: 15px;
                margin-top: 20px;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 15px;
                color: #333333;
                background-color: white;
            }
        """)
        
        energy_layout = QHBoxLayout()
        energy_layout.setSpacing(20)
        energy_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建各能源显示组件
        self.wind_widget = EnergyWidget("风能", self.colors['wind'], DEFAULT_CHINESE_FONT)  
        self.solar_widget = EnergyWidget("太阳能", self.colors['solar'], DEFAULT_CHINESE_FONT)
        self.water_widget = EnergyWidget("水能", self.colors['water'], DEFAULT_CHINESE_FONT)
        
        energy_layout.addWidget(self.wind_widget)
        energy_layout.addWidget(self.solar_widget)
        energy_layout.addWidget(self.water_widget)
        
        energy_group.setLayout(energy_layout)
        layout.addWidget(energy_group)
        
        return tab

    def create_prediction_tab(self):
        """创建预测标签"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 创建预测控制按钮
        control_layout = self.create_prediction_controls()
        layout.addLayout(control_layout)
        
        # 创建预测图表
        self.prediction_widget = PredictionWidget("Microsoft YaHei")
        layout.addWidget(self.prediction_widget)
        
        return tab

    def create_prediction_controls(self):
        """创建预测控制按钮"""
        control_layout = QHBoxLayout()
        
        # 创建24小时预测按钮
        self.update_prediction_btn = QPushButton("更新24小时预测")
        self.update_prediction_btn.setFont(self.normal_font)
        self.update_prediction_btn.clicked.connect(self.on_update_prediction_clicked)
        control_layout.addWidget(self.update_prediction_btn)
        
        # 创建周预测钮
        self.weekly_prediction_btn = QPushButton("查看周预测")
        self.weekly_prediction_btn.setFont(self.normal_font)
        self.weekly_prediction_btn.clicked.connect(self.show_weekly_prediction)
        control_layout.addWidget(self.weekly_prediction_btn)
        
        return control_layout

    def update_displays(self):
        """更新所有显示"""
        if self.is_updating:
            return
            
        try:
            self.is_updating = True
            
            # 更新能源数据
            self.energy_manager.update_energy_data()
            self.update_energy_widgets()
            
            # 更新统计信息
            total_energy = self.energy_manager.current_energy['total']
            self.total_energy_value.setText(f"{total_energy:.1f} kW")
            
            # 计算并更新能源占比
            if total_energy > 0:
                wind_ratio = self.energy_manager.current_energy['wind'] / total_energy * 100
                solar_ratio = self.energy_manager.current_energy['solar'] / total_energy * 100
                water_ratio = self.energy_manager.current_energy['water'] / total_energy * 100
                self.ratio_value.setText(
                    f"风能: {wind_ratio:.1f}% | 阳: {solar_ratio:.1f}% | 能: {water_ratio:.1f}%"
                )
            
            self.update_storage_widget()
            self.update_prediction_widget()
            
            # 更新主要能源显示
            current_energy = self.energy_manager.current_energy
            max_energy = max(
                ('风能', current_energy['wind']),  
                ('太阳能', current_energy['solar']),
                ('水能', current_energy['water']),
                key=lambda x: x[1]
            )
            self.main_energy_label.setText(max_energy[0])
            
            # 根要能源类型设置颜色
            if max_energy[0] == '风能': 
                self.main_energy_label.setStyleSheet("color: #4CAF50;")
            elif max_energy[0] == '太阳能':
                self.main_energy_label.setStyleSheet("color: #FFC107;")
            else:
                self.main_energy_label.setStyleSheet("color: #2196F3;")
            
            self.last_update_time = datetime.now()
            self.error_count = 0
            
        except Exception as e:
            self.error_count += 1
            print(f"更新显示错误: {e}")
            if self.error_count >= 3:
                self.show_error_dialog("更新失败", f"连续更新失败{self.error_count}次，请检查系统状态")
        finally:
            self.is_updating = False

    def show_error_dialog(self, title, message):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)

    def on_update_prediction_clicked(self):
        """处理预更新按钮点击事件"""
        try:
            predictions = self.energy_manager.predict_energy()
            self.prediction_widget.update_prediction(predictions, self.colors)
        except Exception as e:
            print(f"更新预测错误: {e}")

    def show_weekly_prediction(self):
        """显示周预测图表"""
        try:
            weekly_data = self.energy_manager.get_weekly_prediction()
            if not weekly_data:
                return
            
            # 关闭所有已存在的图表窗口
            plt.close('all')
            
            # 创建新图表
            fig = plt.figure(figsize=(12, 6))
            
            dates = [data['date'] for data in weekly_data]
            wind_data = [data['wind'] for data in weekly_data]
            solar_data = [random.uniform(0.5, 2.0) for _ in range(len(weekly_data))]  # 太阳能保持在低值
            water_data = [data['water'] for data in weekly_data]
            
            x = np.arange(len(dates))
            width = 0.25
            
            plt.bar(x - width, wind_data, width, label='风能', color=self.colors['wind'])
            plt.bar(x, solar_data, width, label='太阳能', color=self.colors['solar'])
            plt.bar(x + width, water_data, width, label='水能', color=self.colors['water'])
            
            plt.title('未来7天能源预测')
            plt.xlabel('日期')
            plt.ylabel('预计能源产出 (kW)')
            plt.xticks(x, dates, rotation=45)
            plt.legend()
            plt.tight_layout()
            
            plt.show()
            
        except Exception as e:
            print(f"显示周预测错误: {e}")

    def update_energy_widgets(self):
        """更新能源显示组件"""
        try:
            # 更新风能显示
            wind_value = self.energy_manager.current_energy['wind']
            self.wind_widget.update_value(wind_value)
            
            # 更新太阳能
            solar_value = self.energy_manager.current_energy['solar']
            self.solar_widget.update_value(solar_value)
            
            # 更新水能显示
            water_value = self.energy_manager.current_energy['water']
            self.water_widget.update_value(water_value)
            
        except Exception as e:
            print(f"更新能源组件错误: {e}")

    def update_storage_widget(self):
        """更新储能显示组件"""
        try:
            storage_status = self.energy_manager.storage.get_storage_status()
            self.storage_progress.setValue(int(storage_status['percentage']))
            self.battery_value.setText(f"{storage_status['percentage']}%")
            
            # 更新电动车状态
            if storage_status['ev_charging']:
                self.ev_status_label.setText("充电中")
                self.ev_status_label.setStyleSheet("color: #4CAF50;")
            else:
                self.ev_status_label.setText("未连接")
                self.ev_status_label.setStyleSheet("color: #666666;")
            
            self.ev_progress.setValue(storage_status['ev_battery_level'])
            
            # 更新风扇状态
            running_fans = storage_status.get('running_fans', 3)  # 默认所有风扇运行
            total_fans = 3
            
            # 更新总体状态
            self.fan_status_label.setText(f"{running_fans}/{total_fans} 风扇正运行")
            if running_fans == total_fans:
                self.fan_status_label.setStyleSheet("color: #4CAF50;")  # 绿色
            elif running_fans > 0:
                self.fan_status_label.setStyleSheet("color: #FFC107;")  # 黄色
            else:
                self.fan_status_label.setStyleSheet("color: #F44336;")  # 红色
        except Exception as e:
            print(f"更新储能组件错误: {e}")

    def update_prediction_widget(self):
        """更新预测显示组件"""
        try:
            predictions = self.energy_manager.predict_energy()
            self.prediction_widget.update_prediction(predictions, self.colors)
        except Exception as e:
            print(f"更新预测组件错误: {e}")

    def add_animations(self):
        """添加动画效果"""
        # 为能源组件添加淡入动画
        for widget in [self.wind_widget, self.solar_widget, self.water_widget]:
            animation = QPropertyAnimation(widget, b"windowOpacity")
            animation.setDuration(1000)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            animation.start()

        # 为预测按钮添加悬停动画
        def create_hover_animation(button):
            animation = QPropertyAnimation(button, b"geometry")
            animation.setDuration(200)
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            return animation

        self.update_prediction_btn.enterEvent = lambda e: self.button_hover_enter(self.update_prediction_btn)
        self.update_prediction_btn.leaveEvent = lambda e: self.button_hover_leave(self.update_prediction_btn)
        self.weekly_prediction_btn.enterEvent = lambda e: self.button_hover_enter(self.weekly_prediction_btn)
        self.weekly_prediction_btn.leaveEvent = lambda e: self.button_hover_leave(self.weekly_prediction_btn)

    def button_hover_enter(self, button):
        """按钮悬停进入效果"""
        animation = QPropertyAnimation(button, b"geometry")
        animation.setDuration(200)
        rect = button.geometry()
        animation.setStartValue(rect)
        animation.setEndValue(QRect(rect.x()-2, rect.y()-2, rect.width()+4, rect.height()+4))
        animation.start()

    def button_hover_leave(self, button):
        """按钮悬停离开效果"""
        animation = QPropertyAnimation(button, b"geometry")
        animation.setDuration(200)
        rect = button.geometry()
        animation.setStartValue(rect)
        animation.setEndValue(QRect(rect.x()+2, rect.y()+2, rect.width()-4, rect.height()-4))
        animation.start()

    def create_storage_tab(self):
        """创建储能系统标签页"""
        tab = QWidget()
        layout = QGridLayout(tab)  # 使用网格布局
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建储能状态卡片（左上）
        storage_card = QFrame()
        storage_layout = QVBoxLayout(storage_card)
        storage_layout.setSpacing(15)
        storage_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        storage_title = QLabel("储能状态")
        storage_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        storage_title.setStyleSheet("color: #1976D2;")
        storage_layout.addWidget(storage_title)
        
        # 电量显示
        self.battery_value = QLabel("50%")
        self.battery_value.setFont(QFont(DEFAULT_ENGLISH_FONT, 36, QFont.Bold))
        self.battery_value.setStyleSheet("color: #1976D2;")
        self.battery_value.setAlignment(Qt.AlignCenter)
        storage_layout.addWidget(self.battery_value)
        
        # 进度条
        self.storage_progress = QProgressBar()
        self.storage_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 10px;
                text-align: center;
                min-height: 20px;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1976D2, stop:1 #64B5F6);
                border-radius: 10px;
            }
        """)
        storage_layout.addWidget(self.storage_progress)
        
        storage_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E3F2FD);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        
        # 创建风能发电运行状态卡片（右上）
        fan_card = QFrame()
        fan_layout = QVBoxLayout(fan_card)
        fan_layout.setSpacing(15)
        fan_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        fan_title = QLabel("风能发电运行状态")
        fan_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        fan_title.setStyleSheet("color: #2E7D32;")
        fan_layout.addWidget(fan_title)
        
        # 风扇总状态
        self.fan_status_label = QLabel("0/3 风扇运行中")
        self.fan_status_label.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.fan_status_label.setStyleSheet("color: #F44336;")
        self.fan_status_label.setAlignment(Qt.AlignCenter)
        fan_layout.addWidget(self.fan_status_label)
        
        # 风扇控制按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        for i in range(4):
            btn = QPushButton(f"启用{i}个风扇")
            btn.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
            btn.clicked.connect(lambda checked, count=i: (
                self.serial_manager.send_command(f"FAN{count}"),
                self.update_fan_status(count)  # 确保调用更新风扇状态的方法
            ))
            button_layout.addWidget(btn)
        fan_layout.addLayout(button_layout)
        
        fan_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E8F5E9);
                border-radius: 20px;
                padding: 20px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        # 创建电动车充电状态卡片（下方）
        ev_card = QFrame()
        ev_layout = QVBoxLayout(ev_card)
        ev_layout.setSpacing(15)
        ev_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        ev_title = QLabel("电动车充电状态")
        ev_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        ev_title.setStyleSheet("color: #E65100;")
        ev_layout.addWidget(ev_title)
        
        # 状态显示
        self.ev_status = QLabel("能量驿站充电桩状态正常") 
        self.ev_status.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.ev_status.setStyleSheet("color: #666666;")
        ev_layout.addWidget(self.ev_status)
        
        # 电量进度条
        self.ev_progress = QProgressBar()
        self.ev_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 10px;
                text-align: center;
                min-height: 20px;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E65100, stop:1 #FF9800);
                border-radius: 10px;
            }
        """)
        ev_layout.addWidget(self.ev_progress)
        
        # 充电按钮
        self.ev_button = QPushButton("开始充电")
        self.ev_button.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        self.ev_button.setCheckable(True)
        self.ev_button.clicked.connect(self.toggle_ev_charging)
        self.ev_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                min-height: 40px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        ev_layout.addWidget(self.ev_button)
        
        ev_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #FFF3E0);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        
        # 创建水泵控制卡片
        pump_card = QFrame()
        pump_layout = QVBoxLayout(pump_card)
        pump_layout.setSpacing(15)
        pump_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        pump_title = QLabel("水泵控制")
        pump_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        pump_title.setStyleSheet("color: #1976D2;")
        pump_layout.addWidget(pump_title)
        
        # 状态显示
        self.pump_status = QLabel("水泵状态正常")  # 修改这里
        self.pump_status.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.pump_status.setStyleSheet("color: #F44336;")
        self.pump_status.setAlignment(Qt.AlignCenter)
        pump_layout.addWidget(self.pump_status)
        
        # 水泵控制按钮
        self.pump_button = QPushButton("水泵开关")  # 修改这里
        self.pump_button.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        self.pump_button.setCheckable(True)
        self.pump_button.clicked.connect(self.toggle_pump)
        self.pump_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                min-height: 40px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        pump_layout.addWidget(self.pump_button)
        
        pump_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E3F2FD);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        
        # 创建太阳能状态卡片（左上）
        solar_card = QFrame()
        solar_layout = QVBoxLayout(solar_card)
        solar_layout.setSpacing(15)
        solar_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        solar_title = QLabel("太阳能状态")
        solar_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        solar_title.setStyleSheet("color: #FFC107;")  # 使用太阳能的黄色
        solar_layout.addWidget(solar_title)
        
        # 电量显示
        self.solar_value = QLabel("0%")  # 设置为0%
        self.solar_value.setFont(QFont(DEFAULT_ENGLISH_FONT, 36, QFont.Bold))
        self.solar_value.setStyleSheet("color: #FFC107;")  # 使用太阳能的黄色
        self.solar_value.setAlignment(Qt.AlignCenter)
        solar_layout.addWidget(self.solar_value)
        
        # 进度条
        self.solar_progress = QProgressBar()
        self.solar_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 10px;
                text-align: center;
                min-height: 20px;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFC107, stop:1 #FFE082);  /* 使用太阳能的黄色 */
                border-radius: 10px;
            }
        """)
        solar_layout.addWidget(self.solar_progress)
        
        # 添加状态提示
        self.solar_status = QLabel("当前太阳能不足！")
        self.solar_status.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.solar_status.setStyleSheet("color: #F44336;")  # 使用红色表示警告
        self.solar_status.setAlignment(Qt.AlignCenter)
        solar_layout.addWidget(self.solar_status)
        
        solar_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #FFF8E1);  /* 使用太阳能的浅黄色背景 */
                border-radius: 20px;
                padding: 20px;
            }
        """)
        
        # 创建电动车充电状态卡片（右上）
        ev_card = QFrame()
        ev_layout = QVBoxLayout(ev_card)
        ev_layout.setSpacing(15)
        ev_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        ev_title = QLabel("电动车充电状态")
        ev_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        ev_title.setStyleSheet("color: #E65100;")
        ev_layout.addWidget(ev_title)
        
        # 状态显示
        self.ev_status = QLabel("能量驿站充电桩状态正常")
        self.ev_status.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.ev_status.setStyleSheet("color: #666666;")
        ev_layout.addWidget(self.ev_status)
        
        # 电量进度条
        self.ev_progress = QProgressBar()
        self.ev_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 10px;
                text-align: center;
                min-height: 20px;
                max-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E65100, stop:1 #FF9800);
                border-radius: 10px;
            }
        """)
        ev_layout.addWidget(self.ev_progress)
        
        # 充电按钮
        self.ev_button = QPushButton("充电桩开关")
        self.ev_button.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        self.ev_button.setCheckable(True)
        self.ev_button.clicked.connect(self.toggle_ev_charging)
        self.ev_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                min-height: 40px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        ev_layout.addWidget(self.ev_button)
        
        ev_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #FFF3E0);
                border-radius: 20px;
                padding: 20px;
            }
        """)
        
        # 修改布局中的卡片引用
        layout.addWidget(solar_card, 0, 0)    # 左上（太阳能状态）
        layout.addWidget(ev_card, 0, 1)       # 右上（电动车充电状态）
        layout.addWidget(fan_card, 1, 0)      # 左下（风扇状态）
        layout.addWidget(pump_card, 1, 1)     # 右下（水泵状态）
        
        # 设置行列的拉伸因子
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        
        return tab

    def create_ev_status_card(self):
        """创电动车状态卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E8F5E9);
                border-radius: 20px;
                padding: 20px;
            }
            QLabel {
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("电动车充电状态")
        title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        title.setStyleSheet("color: #2E7D32;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 状态显示
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        
        car_icon = QLabel("🚗")
        car_icon.setFont(QFont("Segoe UI Emoji", 32))
        status_layout.addWidget(car_icon)
        
        self.ev_status = QLabel("未连接")
        self.ev_status.setFont(QFont(DEFAULT_CHINESE_FONT, 20))
        self.ev_status.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.ev_status)
        
        layout.addWidget(status_widget)
        
        # 电量进度条
        self.ev_progress = QProgressBar()
        self.ev_progress.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 10px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E7D32, stop:1 #81C784);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.ev_progress)
        
        # 添加充电按钮
        self.ev_button = QPushButton("开始充电")
        self.ev_button.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        self.ev_button.setCheckable(True)
        self.ev_button.clicked.connect(self.toggle_ev_charging)
        self.ev_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                min-height: 40px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.ev_button)
        
        return card

    def create_fan_status_card(self):
        """创建风扇状态卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E8F5E9);
                border-radius: 20px;
                padding: 20px;
            }
            QLabel {
                background: transparent;
                padding: 5px 0;
                min-height: 35px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                min-width: 120px;
                margin: 5px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题区域
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("能发电运行状态")
        title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        title.setStyleSheet("color: #2E7D32;")
        title.setFixedHeight(40)
        
        icon = QLabel("🌀")
        icon.setFont(QFont("Segoe UI Emoji", 28))
        icon.setFixedHeight(40)
        
        header_layout.addWidget(title)
        header_layout.addWidget(icon)
        layout.addWidget(header)
        
        # 风扇状态区域
        fan_section = QWidget()
        fan_layout = QVBoxLayout(fan_section)
        fan_layout.setSpacing(10)
        
        # 风扇总状态
        self.fan_status_label = QLabel("0/3 风扇运行中")
        self.fan_status_label.setFont(QFont(DEFAULT_CHINESE_FONT, 18))
        self.fan_status_label.setStyleSheet("color: #F44336;")
        self.fan_status_label.setAlignment(Qt.AlignCenter)
        fan_layout.addWidget(self.fan_status_label)
        
        # 风扇状态指示器
        self.fan_indicators = []
        for i in range(3):
            fan_widget = QWidget()
            fan_layout_h = QHBoxLayout(fan_widget)
            fan_layout_h.setContentsMargins(10, 5, 10, 5)
            
            fan_icon = QLabel("🌀")
            fan_icon.setFont(QFont("Segoe UI Emoji", 20))
            fan_layout_h.addWidget(fan_icon)
            
            number_label = QLabel(f"风扇 {i+1}")
            number_label.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
            fan_layout_h.addWidget(number_label)
            
            indicator = QLabel("已停止")
            indicator.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
            indicator.setStyleSheet("color: #F44336;")
            self.fan_indicators.append(indicator)
            fan_layout_h.addWidget(indicator)
            
            fan_layout.addWidget(fan_widget)
        
        # 风扇控制按钮
        fan_control = QWidget()
        fan_control_layout = QHBoxLayout(fan_control)
        fan_control_layout.setSpacing(10)
        
        for i in range(4):
            btn = QPushButton(f"启用{i}个风扇")
            btn.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
            btn.clicked.connect(lambda checked, count=i: (
                self.serial_manager.send_command(f"FAN{count}"),
                self.update_fan_status(count)  # 确保调用更新风扇状态的方法
            ))  # 添加缺失的右括号
            fan_control_layout.addWidget(btn)
        fan_layout.addWidget(fan_control)
        layout.addWidget(fan_section)
        
        return card

    def update_fan_status(self, count):
        """更新风扇状态显示"""
        if 0 <= count <= 3:
            self.fan_count = count
            
            # 更新总状态显示
            self.fan_status_label.setText("风扇状态正常")  # 修改这里
            if count == 3:
                self.fan_status_label.setStyleSheet("color: #4CAF50;")  # 绿色
            elif count > 0:
                self.fan_status_label.setStyleSheet("color: #FFC107;")  # 黄色
            else:
                self.fan_status_label.setStyleSheet("color: #F44336;")  # 红色

    def create_priority_tab(self):
        """创建能源优先级标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建优先级调整卡片
        adjustment_card = QFrame()
        adjustment_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #FFF3E0);
                border-radius: 20px;
                padding: 20px;
            }
            QListWidget {
                background: transparent;
                border: 2px solid #FF9800;
                border-radius: 10px;
                padding: 5px;
                font-size: 16px;
            }
            QListWidget::item {
                background: white;
                border-radius: 8px;
                padding: 10px 25px;
                margin: 5px;
                min-width: 100px;
                max-width: 150px;
            }
            QListWidget::item:selected {
                background: #FFE0B2;
                color: #333333;
            }
            QListWidget::item:hover {
                background: #FFF3E0;
            }
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        adjustment_layout = QVBoxLayout(adjustment_card)
        
        # AI调整标题
        ai_title = QLabel("能源优先级排序")
        ai_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        ai_title.setStyleSheet("color: #F57C00;")
        ai_title.setAlignment(Qt.AlignCenter)
        adjustment_layout.addWidget(ai_title)
        
        # 创建说明标签
        instruction = QLabel("拖动调整优先级顺序（左侧为最高优先级）")
        instruction.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        instruction.setStyleSheet("color: #666666;")
        instruction.setAlignment(Qt.AlignCenter)
        adjustment_layout.addWidget(instruction)
        
        # 创建可拖动的列表
        self.priority_list = QListWidget()
        self.priority_list.setDragDropMode(QListWidget.InternalMove)
        self.priority_list.setMinimumHeight(80)
        self.priority_list.setMaximumHeight(100)
        self.priority_list.setFlow(QListWidget.LeftToRight)
        self.priority_list.setViewMode(QListWidget.ListMode)
        self.priority_list.setWrapping(False)
        self.priority_list.setSpacing(2)
        self.priority_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 添加能源项目
        energy_types = [
            ("风能", "#4CAF50"),
            ("太阳能", "#FFC107"),
            ("水能", "#2196F3")
        ]
        
        # 添加列表项
        for energy_type, color in energy_types:
            item = QListWidgetItem(energy_type)
            item.setTextAlignment(Qt.AlignCenter)
            item.setFont(QFont(DEFAULT_CHINESE_FONT, 18, QFont.Bold))
            item.setForeground(QColor(color))
            item.setSizeHint(QSize(self.priority_list.width() // 3 - 4, 60))
            self.priority_list.addItem(item)
        
        # 添加大小变化事件处理
        def on_list_resize():
            width = self.priority_list.width()
            if width > 0:
                item_width = (width - 20) // 3
                for i in range(self.priority_list.count()):
                    item = self.priority_list.item(i)
                    item.setSizeHint(QSize(item_width, 60))
        
        # 连接大小化信号
        self.priority_list.resizeEvent = lambda e: on_list_resize()
        
        adjustment_layout.addWidget(self.priority_list)
        
        # 添加按区域
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(20)
        
        # AI模式按钮 - 保存为类属性
        self.ai_mode_btn = QPushButton("AI动态调整：关")
        self.ai_mode_btn.setCheckable(True)
        self.ai_mode_btn.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        self.ai_mode_btn.clicked.connect(self.toggle_ai_mode)
        button_layout.addWidget(self.ai_mode_btn)
        
        # 应用按钮
        apply_btn = QPushButton("应用当前顺序")
        apply_btn.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        apply_btn.clicked.connect(self.apply_priority_order)
        button_layout.addWidget(apply_btn)
        
        adjustment_layout.addWidget(button_container)
        
        # 添状态显示
        self.adjustment_status = QLabel("请拖动调整优先级")
        self.adjustment_status.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        self.adjustment_status.setAlignment(Qt.AlignCenter)
        self.adjustment_status.setStyleSheet("color: #666666;")
        adjustment_layout.addWidget(self.adjustment_status)
        
        # 直接添加到主布局
        layout.addWidget(adjustment_card)
        
        return tab

    def toggle_ai_mode(self):
        """切换AI模式"""
        try:
            if self.ai_mode_btn.isChecked():
                self.ai_mode_btn.setText("AI动态调整：开")
                self.adjustment_status.setText("AI动态调整启用")
                self.priority_list.setEnabled(False)
                self.ai_timer.start()
            else:
                self.ai_mode_btn.setText("AI动态调整：关")
                self.adjustment_status.setText("请拖动调整能源优先级")
                self.priority_list.setEnabled(True)
                self.ai_timer.stop()
                # 恢复原优先级显示
                self.priority_list.clear()
                energy_types = [
                    ("风能", "#4CAF50"),
                    ("太阳能", "#FFC107"),
                    ("水能", "#2196F3")
                ]
                for energy_type, color in energy_types:
                    item = QListWidgetItem(energy_type)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFont(QFont(DEFAULT_CHINESE_FONT, 18, QFont.Bold))
                    item.setForeground(QColor(color))
                    item.setSizeHint(QSize(self.priority_list.width() // 3 - 4, 60))
                    self.priority_list.addItem(item)
        except Exception as e:
            print(f"切换AI模式错误: {e}")
            self.ai_mode_btn.setChecked(False)
            self.ai_mode_btn.setText("AI动态调整：关")
            self.priority_list.setEnabled(True)
            self.ai_timer.stop()

    def update_ai_priority(self):
        """AI动态调整优先级"""
        try:
            # 获取当前能源数据
            wind_power = self.energy_manager.current_energy['wind']
            water_power = self.energy_manager.current_energy['water']
            solar_power = 0  # 太阳能设为0
            
            # 获取天气数据
            weather = self.weather_predictor.get_current_weather()
            
            # 根据实际情况调整优先级
            priorities = []
            
            # 根据天气条件判断
            if weather:
                if weather['wind_speed'] > 5:  # 风速较高
                    priorities.append(('风能', "风速条件良好"))
                if weather['humidity'] > 60:  # 湿度较高
                    priorities.append(('水能', "水资源充足"))
                # 添加太阳能
                priorities.append(('太阳能', "当前太阳能不足"))
            
            # 根据实际发电量判断
            remaining = []
            if ('风能', "风速条件良好") not in priorities:
                remaining.append(('风能', wind_power))
            if ('水能', "水资源充足") not in priorities:
                remaining.append(('水能', water_power))
            if ('太阳能', "当前太阳能不足") not in priorities:
                remaining.append(('太阳能', solar_power))
            
            # 按发电量排序
            remaining.sort(key=lambda x: x[1], reverse=True)
            
            # 添加剩余能源
            for energy, power in remaining:
                priorities.append((energy, f"当前产出 {power:.1f}kW"))
            
            # 更新优先级显示
            self.priority_list.clear()
            for i, (energy, reason) in enumerate(priorities):
                item = QListWidgetItem(f"{i+1}. {energy}")
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
                
                # 设置颜色
                if energy == "风能":
                    item.setForeground(QColor("#4CAF50"))
                elif energy == "太阳能":
                    item.setForeground(QColor("#FFC107"))
                else:
                    item.setForeground(QColor("#2196F3"))
                
                self.priority_list.addItem(item)
            
            # 更新状态显示
            status_text = " | ".join([f"{energy}: {reason}" for energy, reason in priorities])
            self.adjustment_status.setText(status_text)
            
        except Exception as e:
            print(f"AI优先级调整错误: {e}")
            self.ai_mode_btn.setChecked(False)
            self.ai_mode_btn.setText("AI动态调整：关")
            self.priority_list.setEnabled(True)
            self.ai_timer.stop()

    def on_priority_changed(self):
        """当优先级顺序改变时更新显示"""
        priorities = []
        priority_levels = {1: "高", 2: "中", 3: "低"}
        
        for i in range(self.priority_list.count()):
            item = self.priority_list.item(i)
            priority_level = priority_levels[i + 1]
            priorities.append(f"{item.text()}: {priority_level}优先级")
        
        self.adjustment_status.setText(" | ".join(priorities))

    def apply_priority_order(self):
        """应用当前优先级顺序"""
        priorities = {}
        for i in range(self.priority_list.count()):
            item = self.priority_list.item(i)
            energy_type = item.text()
            priorities[energy_type] = i + 1
        
        # 更新能源管理器中的优先级
        self.energy_manager.energy_priority = priorities
        
        # 更新状态显示
        self.adjustment_status.setText("优先级更新已应用")

    def create_weather_tab(self):
        """创建天气预报标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建左侧当前天气卡片
        current_weather_card = QFrame()
        current_weather_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E3F2FD);
                border-radius: 20px;
                padding: 15px;  /* 减小内边距 */
            }
            QLabel {
                color: #333333;
                background: transparent;
            }
        """)
        current_weather_layout = QVBoxLayout(current_weather_card)
        current_weather_layout.setSpacing(10)  # 小间距
        current_weather_layout.setContentsMargins(15, 15, 15, 15)  # 减小边距
        
        # 添加位置信息
        location_widget = QWidget()
        location_layout = QVBoxLayout(location_widget)
        location_layout.setSpacing(5)  # 增加行距
        location_layout.setContentsMargins(0, 0, 0, 0)
        
        # 中文位置标题和内容
        location_cn_title = QLabel("当前位置：")
        location_cn_title.setFont(QFont(DEFAULT_CHINESE_FONT, 16, QFont.Bold))
        location_cn_title.setStyleSheet("color: #1976D2;")
        location_cn_title.setAlignment(Qt.AlignLeft)
        location_layout.addWidget(location_cn_title)
        
        location_cn_content = QLabel("金华之光文化广场")
        location_cn_content.setFont(QFont(DEFAULT_CHINESE_FONT, 16, QFont.Bold))
        location_cn_content.setStyleSheet("color: #1976D2;")
        location_cn_content.setAlignment(Qt.AlignLeft)
        location_layout.addWidget(location_cn_content)
        
        # 英文位置标题和内容
        location_en_title = QLabel("Current Location:")
        location_en_title.setFont(QFont(DEFAULT_ENGLISH_FONT, 14, QFont.Bold))
        location_en_title.setStyleSheet("color: #1976D2; font-style: italic;")
        location_en_title.setAlignment(Qt.AlignLeft)
        location_layout.addWidget(location_en_title)
        
        location_en_content = QLabel("Light of Jinhua Cultural Square")
        location_en_content.setFont(QFont(DEFAULT_ENGLISH_FONT, 14, QFont.Bold))
        location_en_content.setStyleSheet("color: #1976D2; font-style: italic;")
        location_en_content.setAlignment(Qt.AlignLeft)
        location_layout.addWidget(location_en_content)
        
        current_weather_layout.addWidget(location_widget)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        line.setFixedHeight(1)
        current_weather_layout.addWidget(line)
        
        # 当前天气标题和图标
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        current_title = QLabel("当前天气状况")
        current_title.setFont(QFont(DEFAULT_CHINESE_FONT, 24, QFont.Bold))
        current_title.setStyleSheet("color: #1976D2;")
        
        self.weather_icon = QLabel("🌤️")  # 保存为类属性
        self.weather_icon.setFont(QFont("Segoe UI Emoji", 32))
        
        header_layout.addWidget(current_title)
        header_layout.addWidget(self.weather_icon)
        current_weather_layout.addWidget(header_widget)
        
        # 天气信息网格
        weather_grid = QWidget()
        grid_layout = QGridLayout(weather_grid)
        grid_layout.setSpacing(10)  # 减小网格间距
        grid_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建天气信息标签
        self.temperature_label = QLabel("--°C")
        self.wind_speed_label = QLabel("-- m/s")
        self.humidity_label = QLabel("--%")
        self.pressure_label = QLabel("-- hPa")
        self.description_label = QLabel("--")
        self.sunlight_label = QLabel("--%")
        
        # 天气信息布局
        weather_items = [
            ("🌡", "温度", self.temperature_label),
            ("💨", "风速", self.wind_speed_label),
            ("💧", "", self.humidity_label),
            ("🌡", "气压", self.pressure_label),
            ("☁", "天气", self.description_label),
            ("🌞", "光照", self.sunlight_label)
        ]
        
        for row, (icon, name, label) in enumerate(weather_items):
            # 图标
            icon_label = QLabel(icon)
            icon_label.setFont(QFont(DEFAULT_ENGLISH_FONT, 24))
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedWidth(40)
            icon_label.setFixedHeight(40)  # 设置固定高度
            grid_layout.addWidget(icon_label, row, 0)
            
            # 名称
            name_label = QLabel(name)
            name_label.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
            name_label.setStyleSheet("""
                color: #666666;
                padding: 5px 0;  /* 增加上下内边距 */
            """)
            name_label.setFixedWidth(60)
            name_label.setFixedHeight(40)  # 设置固定高度
            grid_layout.addWidget(name_label, row, 1)
            
            # 值
            label.setFont(QFont(DEFAULT_ENGLISH_FONT, 18, QFont.Bold))
            label.setStyleSheet("""
                color: #1976D2;
                padding: 5px 0;  /* 增加上下内边距 */
            """)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setMinimumWidth(150)
            label.setFixedHeight(40)  # 设置固定高度
            grid_layout.addWidget(label, row, 2)
        
        # 增加行间距
        grid_layout.setVerticalSpacing(15)  # 置垂直间距
        
        current_weather_layout.addWidget(weather_grid)
        
        # 添加底部空白区
        spacer = QWidget()
        spacer.setFixedHeight(10)
        current_weather_layout.addWidget(spacer)
        
        # 创建右侧天气预报卡片
        forecast_card = QFrame()
        forecast_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 white, stop:1 #E8F5E9);
                border-radius: 20px;
                padding: 20px;
            }
            QLabel {
                color: #333333;
                background: transparent;
            }
            QListWidget {
                background: transparent;
                border: none;
                padding: 20px;
            }
            QListWidget::item {
                background: rgba(255, 255, 255, 0.8);
                border-radius: 15px;
                margin: 15px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid #81C784;
            }
        """)
        forecast_layout = QVBoxLayout(forecast_card)
        forecast_layout.setSpacing(20)
        
        # 天气预报标题
        forecast_title = QLabel("未来天气预报")
        forecast_title.setFont(QFont(DEFAULT_CHINESE_FONT, 28, QFont.Bold))
        forecast_title.setStyleSheet("color: #2E7D32;")
        forecast_title.setAlignment(Qt.AlignCenter)
        forecast_layout.addWidget(forecast_title)
        
        # 预报列表
        self.forecast_list = QListWidget()
        self.forecast_list.setViewMode(QListWidget.IconMode)
        self.forecast_list.setMovement(QListWidget.Static)
        self.forecast_list.setResizeMode(QListWidget.Adjust)
        self.forecast_list.setSpacing(20)
        self.forecast_list.setFlow(QListWidget.LeftToRight)
        self.forecast_list.setWrapping(True)
        self.forecast_list.setUniformItemSizes(True)
        forecast_layout.addWidget(self.forecast_list)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新天气数据")
        refresh_btn.setFont(QFont(DEFAULT_CHINESE_FONT, 16))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 25px;
                font-weight: bold;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        refresh_btn.clicked.connect(self.update_weather_data)
        forecast_layout.addWidget(refresh_btn, alignment=Qt.AlignCenter)
        
        # 添加片到主布局
        layout.addWidget(current_weather_card)
        layout.addWidget(forecast_card)
        
        # 设置左右卡片的宽度比
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)
        
        # 延迟加载天气据
        QTimer.singleShot(500, self.update_weather_data)
        
        return tab

    def update_weather_data(self):
        try:
            # 获取当前天气数
            current_weather = self.weather_predictor.get_current_weather()
            if current_weather:
                # 更新当天气显示
                self.temperature_label.setText(f"{current_weather['temperature']:.1f}°C")
                self.wind_speed_label.setText(f"{current_weather['wind_speed']:.1f} m/s")
                self.humidity_label.setText(f"{current_weather['humidity']}%")
                self.pressure_label.setText(f"{current_weather['pressure']} hPa")
                self.description_label.setText(f"{current_weather['weather_description']}")
                self.sunlight_label.setText(f"{current_weather['sunlight']}%")
                
                # 根据天气描述更新天气图标
                weather_desc = current_weather['weather_description']
                if "晴" in weather_desc:
                    weather_icon = "☀️"
                elif "多云" in weather_desc:
                    weather_icon = "⛅"
                elif "阴" in weather_desc:
                    weather_icon = "☁️"
                elif "雨" in weather_desc:
                    weather_icon = "🌧️"
                elif "" in weather_desc:
                    weather_icon = "🌨️"
                elif "雾" in weather_desc:
                    weather_icon = "🌫️"
                elif "霾" in weather_desc:
                    weather_icon = "😷"
                else:
                    weather_icon = "🌤️"
                
                # 更新气图标
                self.weather_icon.setText(weather_icon)
                self.weather_icon.setFont(QFont("Segoe UI Emoji", 32))
                
            # 获取天气预报
            forecast = self.weather_predictor.get_daily_forecast()
            if forecast:
                self.forecast_list.clear()
                
                # 设列表为垂直局
                self.forecast_list.setViewMode(QListWidget.ListMode)
                self.forecast_list.setFlow(QListWidget.TopToBottom)
                self.forecast_list.setWrapping(False)
                self.forecast_list.setSpacing(10)
                
                # 更新列表样式
                self.forecast_list.setStyleSheet("""
                    QListWidget {
                        background: transparent;
                        border: none;
                        padding: 5px;
                    }
                    QListWidget::item {
                        background: rgba(255, 255, 255, 0.8);
                        border-radius: 10px;
                        padding: 15px 20px;
                        margin: 5px;
                        min-height: 60px;
                    }
                """)
                
                for day in forecast[:6]:  # 显示6天预报
                    # 创建列表项
                    item = QListWidgetItem()
                    item.setSizeHint(QSize(self.forecast_list.viewport().width() - 40, 65))
                    
                    # 获取天气图标
                    weather_icon = self.get_weather_icon(day['weather'])
                    
                    # 建文内容
                    text = (f"{day['date'][5:].replace('-', '')}日    "
                           f"{weather_icon} {day['weather']}    "
                           f" {day['temp_min']:.0f}°C ~ {day['temp_max']:.0f}°C    "
                           f"💨 {day['wind_speed']:.0f}m/s    "
                           f"💧 {day['humidity']}%")
                    
                    item.setText(text)
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    item.setFont(QFont(DEFAULT_CHINESE_FONT, 16))  # 改回更合理的字大小
                    
                    # 根据天气设置背景色
                    if "晴" in day['weather']:
                        item.setBackground(QColor("#FFF8E1"))
                    elif "雨" in day['weather']:
                        item.setBackground(QColor("#E3F2FD"))
                    elif "云" in day['weather'] or "阴" in day['weather']:
                        item.setBackground(QColor("#F5F5F5"))
                    else:
                        item.setBackground(QColor("#FFFFFF"))
                    
                    self.forecast_list.addItem(item)
                    
        except Exception as e:
            print(f"更新天气数据错误: {e}")

    def get_weather_icon(self, weather):
        """获取天气图标"""
        icons = {
            "晴": "☀️",
            "多云": "⛅",
            "阴": "☁️",
            "雨": "🌧️",
            "雪": "🌨️",
            "雾": "🌫️",
            "霾": "😷"
        }
        for key, icon in icons.items():
            if key in weather:
                return icon
        return "❓"

    def get_weather_style(self, weather):
        """获取气卡片样"""
        if "" in weather:
            return """
                QFrame {
                    background-color: #FFF8E1;
                    border: 2px solid #FFB300;
                    border-radius: 15px;
                }
            """
        elif "雨" in weather:
            return """
                QFrame {
                    background-color: #E3F2FD;
                    border: 2px solid #1E88E5;
                    border-radius: 15px;
                }
            """
        elif "云" in weather or "阴" in weather:
            return """
                QFrame {
                    background-color: #F5F5F5;
                    border: 2px solid #757575;
                    border-radius: 15px;
                }
            """
        else:
            return """
                QFrame {
                    background-color: #FFFFFF;
                    border: 2px solid #78909C;
                    border-radius: 15px;
                }
            """

    def toggle_pump(self):
        """切换水泵状态"""
        try:
            if not self.pump_button.isChecked():
                # 开启水泵
                if self.serial_manager.control_water_pump(True):
                    self.pump_button.setChecked(True)
                    self.pump_button.setText("关闭水泵")
                    self.pump_status.setText("水泵运行中")
                    self.pump_status.setStyleSheet("color: #4CAF50;")
                    self.serial_manager.water_pump_start_time = time.time()
            else:
                # 关闭水泵
                if self.serial_manager.control_water_pump(False):
                    self.pump_button.setChecked(False)
                    self.pump_button.setText("开启水泵")
                    self.pump_status.setText("水泵已关闭")
                    self.pump_status.setStyleSheet("color: #F44336;")
                    self.serial_manager.water_pump_start_time = None
        except Exception as e:
            print(f"切换水泵状态错误: {e}")

    def update_serial_status(self):
        """定更新串口状和能源数据"""
        try:
            # 更新风扇状态和风能
            if self.fan_count > 0:
                wind_power = self.fan_count * 20  # 每个风扇20kW
                self.serial_manager.control_fans(self.fan_count)
            else:
                wind_power = 0
                
            # 更水泵状态和水能
            water_power = self.serial_manager.get_water_power()
            
            # 更新电充电状态
            if self.ev_charging_start_time is not None:
                charging_time = time.time() - self.ev_charging_start_time
                charge_increment = (charging_time / 60) * 10  # 每分钟充电10%
                self.ev_battery_level = min(100, self.ev_battery_level + charge_increment)
                
                if self.ev_battery_level >= 100:
                    # 电池充满，停止充电
                    self.ev_charging_start_time = None
                    self.serial_manager.control_ev_charging(False)
                    self.ev_status_label.setText("充电完成")
                    self.ev_status_label.setStyleSheet("color: #4CAF50;")
            
            # 更新能源数据
            self.current_energy.update({
                'wind': wind_power,
                'solar': 0,
                'water': water_power,
                'total': wind_power + water_power
            })
            
            # 更新显示
            self.update_displays()
            
        except Exception as e:
            print(f"更串口状态错误: {e}")

    def toggle_ev_charging(self):
        """切换电动车充电状态"""
        try:
            if not self.ev_button.isChecked():
                # 开始充电
                if self.serial_manager.control_ev_charging(True):
                    self.ev_button.setChecked(True)
                    self.ev_button.setText("停止充电")
                    self.ev_status.setText("充电中")
                    self.ev_status.setStyleSheet("color: #4CAF50;")
                    self.ev_charging_start_time = time.time()
            else:
                # 停止充电
                if self.serial_manager.control_ev_charging(False):
                    self.ev_button.setChecked(False)
                    self.ev_button.setText("开始充电")
                    self.ev_status.setText("充电已停止")
                    self.ev_status.setStyleSheet("color: #F44336;")
                    self.ev_charging_start_time = None
        except Exception as e:
            print(f"切换电动车充电状态错误: {e}")

    def update_energy_display(self, energy_data):
        """更新能源显示"""
        try:
            # 更新各能源显示
            self.wind_widget.update_value(energy_data['wind'])
            self.solar_widget.update_value(energy_data['solar'])
            self.water_widget.update_value(energy_data['water'])
            
            # 更新总能源显示
            total_power = energy_data['total']
            self.total_energy_value.setText(f"{total_power:.1f} kW")
            
            # 更新能源占比
            if total_power > 0:
                wind_ratio = (energy_data['wind'] / total_power) * 100
                water_ratio = (energy_data['water'] / total_power) * 100
                self.ratio_value.setText(
                    f"风能: {wind_ratio:.1f}% | 太阳能: 0% | 水能: {water_ratio:.1f}%"
                )
            else:
                self.ratio_value.setText("风能: 0% | 太阳能: 0% | 水能: 0%")
                
        except Exception as e:
            print(f"更新能源显示错误: {e}")

    def closeEvent(self, event):
        """程序关闭时的处理"""
        try:
            if hasattr(self, 'serial_manager'):
                self.serial_manager.disconnect()
                print("串口已断开连接")
        except Exception as e:
            print(f"关闭串时出错: {e}")
        event.accept()

    def update_status(self):
        """更新所有状态显示"""
        try:
            
            wind_power = random.uniform(10, 30)
            
            # 更新水泵发电量
            water_power = self.serial_manager.get_water_power()
            
            # 更新能源数据
            self.energy_manager.current_energy.update({
                'wind': wind_power,
                'solar': 0,  # 保持太阳能显示但值为0
                'water': water_power,
                'total': wind_power + water_power
            })
            
            # 更新显示
            self.update_energy_display(self.energy_manager.current_energy)
            
        except Exception as e:
            print(f"更新状态错误: {e}")

    def update_water_pump_status(self, on):
        """更新水泵状态显示"""
        if on:
            self.pump_button.setText("关闭水泵")
            self.pump_status.setText("水泵运行中")
            self.pump_status.setStyleSheet("color: #4CAF50;")
        else:
            self.pump_button.setText("开启水泵")
            self.pump_status.setText("水泵已关闭")
            self.pump_status.setStyleSheet("color: #F44336;")

    def update_ev_charging_status(self, charging):
        """更新电动车充电状态显示"""
        if charging:
            self.ev_button.setText("停止充电")
            self.ev_status.setText("充电中")
            self.ev_status.setStyleSheet("color: #4CAF50;")
        else:
            self.ev_button.setText("开始充电")
            self.ev_status.setText("充电已停")
            self.ev_status.setStyleSheet("color: #F44336;")

    def update_fan_status(self, count):
        """更新风扇状态显示"""
        if 0 <= count <= 3:
            self.fan_count = count
            
            # 更新总状态显示
            self.fan_status_label.setText(f"风扇状态正常")
            if count == 3:
                self.fan_status_label.setStyleSheet("color: #4CAF50;")  # 绿色
            elif count > 0:
                self.fan_status_label.setStyleSheet("color: #FFC107;")  # 黄
            else:
                self.fan_status_label.setStyleSheet("color: #F44336;")  # 红色

class SerialManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, dashboard=None):
        if not hasattr(self, 'initialized'):
            self.dashboard = dashboard
            self.port = 'COM4'
            self.baudrate = 115200
            self.serial = None
            self.is_connected = False
            self.water_pump_start_time = None
            self.fan_count = 0
            self.initialized = True
            print("SerialManager 初始化完")
    
    def connect(self):
        """连接串口"""
        if self.is_connected:
            print("串口已经连接")
            return True
            
        try:
            if self.serial is None or not self.serial.is_open:
                print(f"尝试连接串 {self.port}")
                self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
                self.is_connected = True
                print(f"成功连接到串口 {self.port}")
                return True
        except Exception as e:
            print(f"串口连接失败: {e}")
            self.is_connected = False
            return False
    
    def send_command(self, command):
        """发送命令到串口"""
        if self.is_connected:
            try:
                full_command = f"{command}\r\n"  # 添加两个空字符
                self.serial.write(full_command.encode('gbk'))
                print(f"发送命令: {command}")
                return True
            except Exception as e:
                print(f"发送命令失败: {e}")
                return False
        return False
    
    def control_fans(self, count):
        """控制风扇数量"""
        if 0 <= count <= 3:
            if self.send_command(f"FAN{count}"):  # 发送FAN0到FAN3的命令
                self.fan_count = count
                if self.dashboard:
                    self.dashboard.update_fan_status(count)  
                print(f"已设置风扇数量为: {count}")
                return True
        return False
    
    def control_water_pump(self, on=True):
        """控制水泵"""
        if on:
            if self.send_command("WATER"):  # 发送WATER命令开启水泵
                self.water_pump_start_time = time.time()
                if self.dashboard:
                    self.dashboard.update_water_pump_status(True)  
                print("已开启水泵")
                return True
        else:
            if self.send_command("OFF"):  # 发送OFF命令关闭水泵
                self.water_pump_start_time = None
                if self.dashboard:
                    self.dashboard.update_water_pump_status(False)  
                print("已关闭水泵")
                return True
        return False
    
    def get_water_power(self):
        """计算水泵发效率"""
        if self.water_pump_start_time is None:
            return 0
        running_time = time.time() - self.water_pump_start_time
        power = min(running_time / 60 * 0.5, 30)  # 每分钟0.5kW，最大30kW
        return power
    
    def disconnect(self):
        """断开串口连接"""
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
                self.is_connected = False
                print(f"已断开串口 {self.port} 的连接")
        except Exception as e:
            print(f"断开串口连接时出错: {e}")
    
    def control_ev_charging(self, charging=True):
        """控制电动车充电"""
        if charging:
            if self.send_command("CAR"):  # 发送CAR命令开启充电
                if self.dashboard:
                    self.dashboard.ev_button.setText("停止充电")  
                    self.dashboard.ev_status.setText("充电中")
                    self.dashboard.ev_status.setStyleSheet("color: #4CAF50;")
                print("已开启电动车充电")
                return True
        else:
            if self.send_command("BAN"):  # 发送BAN命令停止充电
                if self.dashboard:
                    self.dashboard.ev_button.setText("开始充电")  
                    self.dashboard.ev_status.setText("充电已停止")  
                    self.dashboard.ev_status.setStyleSheet("color: #F44336;")
                print("已停止电动车充电")
                return True
        return False

# 创建全局单例
SERIAL_MANAGER = SerialManager()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    dashboard = EnergyDashboard()
    dashboard.show()
    
    # 运行应用程序
    sys.exit(app.exec_())
