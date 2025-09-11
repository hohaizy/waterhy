import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, \
    QGroupBox, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt


class ReservoirConfig:
    def __init__(self, rivers, data_type="daily"):
        self.rivers = rivers  # 包含河流系统的所有数据
        self.data_type = data_type  # 逐日或逐小时数据

    def to_dict(self):
        """将配置转换为字典"""
        return {
            "rivers": [river.to_dict() for river in self.rivers],
            "data_type": self.data_type
        }

    def save_to_json(self, file_path):
        """将配置保存为 JSON 文件"""
        config_dict = self.to_dict()
        with open(file_path, 'w') as json_file:
            json.dump(config_dict, json_file, indent=4, ensure_ascii=False)
        print(f"配置文件已保存到 {file_path}")


class RiverSystem:
    def __init__(self, river_name, is_main_stream=True, tributaries=None):
        self.river_name = river_name  # 河流名称
        self.reservoirs = []  # 这个字段会动态保存每条河流下的水库
        self.is_main_stream = is_main_stream  # 是否为干流
        self.tributaries = tributaries if tributaries else []  # 支流（如果有的话）

    def add_reservoir(self, reservoir_name):
        """添加水库到河流"""
        self.reservoirs.append(reservoir_name)

    def delete_reservoir(self, river_system, reservoir_name):
        """删除指定水库"""
        river_system.delete_reservoir(reservoir_name)
        print(f"删除水库：{reservoir_name}")

        # 遍历布局，查找水库控件
        for i in reversed(range(self.main_layout.count())):
            widget = self.main_layout.itemAt(i).widget()

            # 检查布局项是否是水库控件
            if widget and isinstance(widget, QHBoxLayout):
                for j in range(widget.count()):
                    sub_widget = widget.itemAt(j).widget()

                    # 找到并移除水库控件
                    if isinstance(sub_widget, QLabel) and sub_widget.text() == f"水库：{reservoir_name}":
                        # 从布局中移除水库控件
                        widget.removeWidget(sub_widget)

                        # 解除控件和布局的绑定
                        sub_widget.setParent(None)

                        # 安全删除控件
                        sub_widget.deleteLater()
                        print(f"已删除界面上的水库：{reservoir_name}")
                        break  # 确保删除后跳出循环

    def delete(self):
        """删除当前河流及所有水库"""
        self.reservoirs.clear()

    def to_dict(self):
        """将河流系统转换为字典"""
        return {
            "river_name": self.river_name,
            "is_main_stream": self.is_main_stream,  # 判断是否是干流
            "reserves": self.reservoirs,  # 保存所有水库
            "tributaries": [tributary.to_dict() for tributary in self.tributaries]  # 支流信息
        }


class Tributary:
    def __init__(self, tributary_name, insertion_river, insertion_point, location="上游"):
        self.tributary_name = tributary_name  # 支流名称
        self.insertion_river = insertion_river  # 支流插入的河流
        self.insertion_point = insertion_point  # 支流插入的位置（如"水库2"）
        self.location = location  # 插入位置是 "上游" 还是 "下游"

    def to_dict(self):
        """将支流转换为字典"""
        return {
            "tributary_name": self.tributary_name,
            "insertion_river": self.insertion_river,
            "insertion_point": self.insertion_point,
            "location": self.location  # 上游或下游
        }


class ConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('水库调度项目配置')
        self.setGeometry(100, 100, 600, 600)

        # 初始化界面
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 配置表单
        form_layout = QFormLayout()

        # 数据类型：逐日或逐小时
        self.data_type_input = QComboBox()
        self.data_type_input.addItems(['逐日', '逐小时'])
        form_layout.addRow('数据类型：', self.data_type_input)

        # 添加河流按钮
        self.add_river_btn = QPushButton('添加河流')
        self.add_river_btn.clicked.connect(self.add_river)
        form_layout.addRow(self.add_river_btn)

        # 保存配置文件按钮
        self.save_config_btn = QPushButton('保存配置')
        self.save_config_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_config_btn)

        # 主要布局
        self.main_layout = QVBoxLayout()

        layout.addLayout(form_layout)
        layout.addLayout(self.main_layout)

        self.setLayout(layout)

        self.rivers = []  # 用于保存所有的河流系统

    def add_river(self):
        """添加新河流"""
        # 根据已添加河流的数量，动态生成河流名称
        river_name = f"河流{len(self.rivers) + 1}"

        river_group = QGroupBox(f"河流：{river_name}")
        river_layout = QVBoxLayout()

        # 输入河流名称
        self.river_name_input = QLineEdit()
        self.river_name_input.setPlaceholderText("请输入河流名称")
        river_layout.addWidget(QLabel('河流名称：'))
        river_layout.addWidget(self.river_name_input)

        # 选择河流类型（干流或支流）
        self.river_type_input = QComboBox()
        self.river_type_input.addItems(['干流', '支流'])
        river_layout.addWidget(QLabel('河流类型：'))
        river_layout.addWidget(self.river_type_input)

        # 如果是支流，选择插入的干流和插入位置
        self.tributary_insertion_river_input = QComboBox()
        self.tributary_insertion_river_input.addItem('干流1')  # 初始干流1，后面可根据实际动态生成
        self.tributary_insertion_river_input.setEnabled(False)
        self.tributary_insertion_input = QLineEdit()
        self.tributary_insertion_input.setPlaceholderText("如：第 2 个水库")
        self.tributary_insertion_input.setEnabled(False)

        self.river_type_input.currentIndexChanged.connect(self.toggle_tributary_options)

        river_layout.addWidget(QLabel('插入干流：'))
        river_layout.addWidget(self.tributary_insertion_river_input)
        river_layout.addWidget(QLabel('插入位置：'))
        river_layout.addWidget(self.tributary_insertion_input)

        # 添加按钮：添加水库到河流
        self.add_reservoir_btn = QPushButton('添加水库')
        self.add_reservoir_btn.clicked.connect(self.add_reservoir)
        river_layout.addWidget(self.add_reservoir_btn)

        # 删除河流按钮
        self.delete_river_btn = QPushButton('删除河流')
        self.delete_river_btn.clicked.connect(self.delete_river)
        river_layout.addWidget(self.delete_river_btn)

        river_group.setLayout(river_layout)
        self.main_layout.addWidget(river_group)

        # 创建一个新的河流系统
        new_river = RiverSystem(river_name, is_main_stream=True)
        self.rivers.append(new_river)

    def toggle_tributary_options(self):
        """切换支流的插入选项"""
        if self.river_type_input.currentText() == '支流':
            self.tributary_insertion_river_input.setEnabled(True)
            self.tributary_insertion_input.setEnabled(True)
        else:
            self.tributary_insertion_river_input.setEnabled(False)
            self.tributary_insertion_input.setEnabled(False)

    def add_reservoir(self):
        """为当前河流添加水库"""
        current_river = self.rivers[-1]  # 当前操作的是最新添加的河流
        # 添加一个输入框让用户命名水库
        reservoir_name_input = QLineEdit()
        reservoir_name_input.setPlaceholderText("请输入水库名称")

        # 添加水库名称输入框
        confirm_button = QPushButton("确认添加水库")
        confirm_button.clicked.connect(lambda: self.confirm_add_reservoir(current_river, reservoir_name_input.text()))

        # 将输入框和按钮添加到布局中
        layout = QVBoxLayout()
        layout.addWidget(QLabel("水库名称："))
        layout.addWidget(reservoir_name_input)
        layout.addWidget(confirm_button)

        # 创建一个小组框用于水库输入
        group_box = QGroupBox("输入水库名称")
        group_box.setLayout(layout)

        self.main_layout.addWidget(group_box)

    def confirm_add_reservoir(self, current_river, reservoir_name):
        """确认添加水库"""
        if reservoir_name:  # 如果用户输入了水库名称
            current_river.add_reservoir(reservoir_name)
            print(f"添加水库：{reservoir_name}")
            # 更新界面显示水库
            new_reservoir_label = QLabel(f"水库：{reservoir_name}")
            delete_button = QPushButton("删除水库")
            delete_button.clicked.connect(lambda: self.delete_reservoir(current_river, reservoir_name))

            delete_layout = QHBoxLayout()
            delete_layout.addWidget(new_reservoir_label)
            delete_layout.addWidget(delete_button)

            self.main_layout.addLayout(delete_layout)

    def delete_reservoir(self, river_system, reservoir_name):
        """删除指定水库"""
        river_system.delete_reservoir(reservoir_name)
        print(f"删除水库：{reservoir_name}")

        # 更新界面，移除水库相关的显示组件
        for i in reversed(range(self.main_layout.count())):
            widget = self.main_layout.itemAt(i).widget()
            if widget and isinstance(widget, QHBoxLayout):
                for j in range(widget.count()):
                    sub_widget = widget.itemAt(j).widget()
                    if isinstance(sub_widget, QLabel) and sub_widget.text() == f"水库：{reservoir_name}":
                        widget.deleteLater()

    def delete_river(self):
        """删除当前河流"""
        current_river = self.rivers[-1]  # 当前操作的是最新添加的河流
        self.rivers.remove(current_river)  # 从列表中删除河流
        print(f"删除河流：{current_river.river_name}")

        # 删除界面中对应的河流控件
        for i in reversed(range(self.main_layout.count())):
            widget = self.main_layout.itemAt(i).widget()
            if widget and isinstance(widget, QGroupBox) and widget.title() == f"河流：{current_river.river_name}":
                widget.deleteLater()

    def save_config(self):
        """保存配置到 JSON 文件"""
        try:
            # 获取数据类型（逐日或逐小时）
            data_type = self.data_type_input.currentText()

            # 例如：这里假设有一个河流，并添加了水库
            river_system = self.rivers[0]
            if self.river_type_input.currentText() == '支流':
                tributary = Tributary("支流1", "干流1", "第 2 个水库")
                river_system.tributaries.append(tributary)

            # 创建配置并保存
            config = ReservoirConfig(self.rivers, data_type)
            config.save_to_json('project_config.json')  # 保存为 JSON 文件

            print("配置保存成功！")
        except Exception as e:
            print(f"保存配置时出错：{e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec_())
