import sys
import json
from typing import List, Dict, Set

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton,
    QGroupBox, QLabel, QHBoxLayout, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt


# ---------------------- 数据模型 ----------------------
class ReservoirConfig:
    def __init__(self, rivers: List["RiverSystem"], data_type: str = "daily"):
        self.rivers = rivers
        self.data_type = data_type  # "daily" | "hourly"

    def to_dict(self) -> Dict:
        return {
            "rivers": [r.to_dict() for r in self.rivers],
            "data_type": self.data_type
        }

    def save_to_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)


class RiverSystem:
    def __init__(self, river_name: str, is_main_stream: bool = True, reservoirs: List[str] = None):
        self.river_name = river_name
        self.is_main_stream = is_main_stream
        self.reservoirs = reservoirs[:] if reservoirs else []
        self.tributaries: List[Tributary] = []

    def add_reservoir(self, name: str):
        if name and name not in self.reservoirs:
            self.reservoirs.append(name)

    def remove_reservoir(self, name: str):
        if name in self.reservoirs:
            self.reservoirs.remove(name)

    def to_dict(self) -> Dict:
        return {
            "river_name": self.river_name,
            "is_main_stream": self.is_main_stream,
            "reservoirs": self.reservoirs,
            "tributaries": [t.to_dict() for t in self.tributaries]
        }


class Tributary:
    def __init__(self, tributary_name: str, insertion_river: str, insertion_point: str, location: str = "上游"):
        self.tributary_name = tributary_name
        self.insertion_river = insertion_river  # 目标河流（可为干流或支流）
        self.insertion_point = insertion_point  # 如 “第 2 个水库” / “某水库名”
        self.location = location                # "上游" | "下游"

    def to_dict(self) -> Dict:
        return {
            "tributary_name": self.tributary_name,
            "insertion_river": self.insertion_river,
            "insertion_point": self.insertion_point,
            "location": self.location
        }


# ---------------------- UI 组件：单条河流组 ----------------------
class RiverGroup(QGroupBox):
    """
    每条河流自己的控件组：名字、类型、（若为支流）插入目标/位置/上下游，水库增删。
    """
    def __init__(self, parent_window: "ConfigWindow", index: int):
        super().__init__(f"河流：河流{index + 1}")
        self.parent_window = parent_window

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入河流名称")

        self.type_combo = QComboBox()
        self.type_combo.addItems(["干流", "支流"])

        # 支流插入设置（目标可以是任何河流：干流或支流）
        self.insert_group = QWidget()
        insert_layout = QFormLayout(self.insert_group)
        self.insert_target_combo = QComboBox()
        self.insert_point_edit = QLineEdit()
        self.insert_point_edit.setPlaceholderText("如：第 2 个水库 / 某水库名")
        self.location_combo = QComboBox()
        self.location_combo.addItems(["上游", "下游"])

        insert_layout.addRow("插入目标河流：", self.insert_target_combo)
        insert_layout.addRow("插入位置：", self.insert_point_edit)
        insert_layout.addRow("位置关系：", self.location_combo)

        # 水库列表（每个水库一行行容器）
        self.res_list_container = QWidget()
        self.res_list_layout = QVBoxLayout(self.res_list_container)
        self.res_list_layout.setContentsMargins(0, 0, 0, 0)

        # 添加水库行
        self.res_name_edit = QLineEdit()
        self.res_name_edit.setPlaceholderText("输入水库名称")
        self.res_add_btn = QPushButton("添加水库")
        self.res_add_btn.clicked.connect(self.on_add_reservoir)

        res_add_row = QWidget()
        res_add_row_layout = QHBoxLayout(res_add_row)
        res_add_row_layout.setContentsMargins(0, 0, 0, 0)
        res_add_row_layout.addWidget(QLabel("水库名称："))
        res_add_row_layout.addWidget(self.res_name_edit)
        res_add_row_layout.addWidget(self.res_add_btn)

        # 删除本河流
        self.delete_btn = QPushButton("删除本河流")
        self.delete_btn.clicked.connect(self.on_delete_me)

        # 总体布局
        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("河流名称：", self.name_edit)
        form.addRow("河流类型：", self.type_combo)
        lay.addLayout(form)
        lay.addWidget(self.insert_group)
        lay.addWidget(QLabel("水库列表："))
        lay.addWidget(self.res_list_container)
        lay.addWidget(res_add_row)
        lay.addWidget(self.delete_btn, alignment=Qt.AlignRight)

        # 事件
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.name_edit.textChanged.connect(lambda _: self.parent_window.on_river_type_or_name_changed())
        self._on_type_changed()  # 初始化隐藏/显示
        self.refresh_insert_targets()

    # 由父窗口调用：当任意河流的类型或名字变化时刷新支流的“插入目标河流”下拉
    def refresh_insert_targets(self):
        is_tributary = (self.type_combo.currentText() == "支流")
        self.insert_target_combo.clear()
        if is_tributary:
            current_name = self.get_river_name()
            all_rivers = self.parent_window.get_current_river_names(exclude=current_name)
            if not all_rivers:
                self.insert_target_combo.addItem("（暂无可选目标）")
                self.insert_target_combo.setEnabled(False)
            else:
                self.insert_target_combo.addItems(all_rivers)
                self.insert_target_combo.setEnabled(True)

    def _on_type_changed(self):
        is_tributary = (self.type_combo.currentText() == "支流")
        self.insert_group.setVisible(is_tributary)
        self.refresh_insert_targets()
        self.parent_window.on_river_type_or_name_changed()

    def on_add_reservoir(self):
        name = self.res_name_edit.text().strip()
        if not name:
            return
        # 检查重复
        if any(self._row_label_text(row) == name for row in self._iter_reservoir_rows()):
            QMessageBox.warning(self, "提示", f"已存在名为“{name}”的水库。")
            return
        row = self._make_reservoir_row(name)
        self.res_list_layout.addWidget(row)
        self.res_name_edit.clear()

    def _make_reservoir_row(self, name: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(name)
        btn = QPushButton("删除")
        btn.clicked.connect(lambda: self._remove_reservoir_row(row))
        layout.addWidget(QLabel("水库："))
        layout.addWidget(lbl)
        layout.addStretch(1)
        layout.addWidget(btn)
        return row

    def _remove_reservoir_row(self, row_widget: QWidget):
        self.res_list_layout.removeWidget(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def _iter_reservoir_rows(self):
        for i in range(self.res_list_layout.count()):
            w = self.res_list_layout.itemAt(i).widget()
            if isinstance(w, QWidget):
                yield w

    @staticmethod
    def _row_label_text(row_widget: QWidget) -> str:
        labels = row_widget.findChildren(QLabel)
        for lab in labels:
            if lab.text() and lab.text() != "水库：":
                return lab.text().strip()
        return ""

    # -------- 持久化读取 --------
    def get_river_name(self) -> str:
        return self.name_edit.text().strip() or self.title().replace("河流：", "").strip()

    def is_main_stream(self) -> bool:
        return self.type_combo.currentText() == "干流"

    def get_reservoir_names(self) -> List[str]:
        return [self._row_label_text(w) for w in self._iter_reservoir_rows() if self._row_label_text(w)]

    def get_tributary_link(self) -> Tributary:
        """仅当自身是支流时，返回挂接信息；否则返回 None"""
        if self.is_main_stream():
            return None
        trib_name = self.get_river_name()
        target = self.insert_target_combo.currentText().strip()
        point = self.insert_point_edit.text().strip() or "未指定"
        loc = self.location_combo.currentText()
        return Tributary(trib_name, target, point, loc)

    def on_delete_me(self):
        self.parent_window.delete_river_group(self)


# ---------------------- 主窗口 ----------------------
class ConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("水库调度项目配置")
        self.resize(820, 680)

        self.river_groups: List[RiverGroup] = []

        root = QVBoxLayout(self)

        # 顶部表单：数据类型 + 操作按钮
        top_form = QFormLayout()
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["逐日", "逐小时"])  # 将映射为 daily/hourly
        top_form.addRow("数据类型：", self.data_type_combo)

        self.btn_add_river = QPushButton("添加河流")
        self.btn_add_river.clicked.connect(self.add_river_group)

        self.btn_save = QPushButton("保存配置")
        self.btn_save.clicked.connect(self.on_save)

        top_btn_row = QWidget()
        top_btn_lay = QHBoxLayout(top_btn_row)
        top_btn_lay.setContentsMargins(0, 0, 0, 0)
        top_btn_lay.addWidget(self.btn_add_river)
        top_btn_lay.addStretch(1)
        top_btn_lay.addWidget(self.btn_save)

        root.addLayout(top_form)
        root.addWidget(top_btn_row)

        # 中间滚动区放多个河流组
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_lay = QVBoxLayout(self.scroll_content)
        self.scroll_lay.addStretch(1)
        self.scroll.setWidget(self.scroll_content)
        root.addWidget(self.scroll)

    # --------- 供子组回调：类型/名字变化时刷新所有“插入目标河流” ----------
    def on_river_type_or_name_changed(self):
        for grp in self.river_groups:
            grp.refresh_insert_targets()

    def get_current_river_names(self, exclude: str = "") -> List[str]:
        names = []
        for grp in self.river_groups:
            nm = grp.get_river_name()
            if nm and nm != exclude:
                names.append(nm)
        # 可选：去重（避免用户误重名）
        uniq = []
        for n in names:
            if n not in uniq:
                uniq.append(n)
        return uniq

    # --------- 添加/删除 河流组 ----------
    def add_river_group(self):
        idx = len(self.river_groups)
        grp = RiverGroup(self, idx)
        self.scroll_lay.insertWidget(self.scroll_lay.count() - 1, grp)
        self.river_groups.append(grp)
        self.on_river_type_or_name_changed()

    def delete_river_group(self, grp: RiverGroup):
        if grp in self.river_groups:
            self.river_groups.remove(grp)
            grp.setParent(None)
            grp.deleteLater()
            self.on_river_type_or_name_changed()

    # --------- 拓扑环检测（支流→目标的有向边） ----------
    @staticmethod
    def _has_cycle(edges: List[tuple]) -> bool:
        graph: Dict[str, List[str]] = {}
        for a, b in edges:  # a -> b
            graph.setdefault(a, []).append(b)
            graph.setdefault(b, [])
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {node: WHITE for node in graph}

        def dfs(u: str) -> bool:
            color[u] = GRAY
            for v in graph[u]:
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and dfs(v):
                    return True
            color[u] = BLACK
            return False

        for node in list(graph.keys()):
            if color[node] == WHITE and dfs(node):
                return True
        return False

    # --------- 保存 ----------
    def on_save(self):
        try:
            # 映射数据类型
            dt_text = self.data_type_combo.currentText()
            data_type = "daily" if dt_text == "逐日" else "hourly"

            # 组装所有河流
            name_to_system: Dict[str, RiverSystem] = {}
            tributary_links: List[Tributary] = []

            for grp in self.river_groups:
                name = grp.get_river_name()
                if not name:
                    continue
                sys_obj = RiverSystem(
                    river_name=name,
                    is_main_stream=grp.is_main_stream(),
                    reservoirs=grp.get_reservoir_names()
                )
                if name in name_to_system:
                    QMessageBox.warning(self, "提示", f"存在重名河流：{name}，请修改后重试。")
                    return
                name_to_system[name] = sys_obj
                link = grp.get_tributary_link()
                if link:
                    tributary_links.append(link)

            # 校验：插入目标必须存在
            for link in tributary_links:
                if link.insertion_river not in name_to_system:
                    QMessageBox.warning(self, "提示", f"支流“{link.tributary_name}”的插入目标“{link.insertion_river}”不存在。")
                    return

            # 环检测：a(支流) -> b(目标河流)
            edges = [(t.tributary_name, t.insertion_river) for t in tributary_links]
            if self._has_cycle(edges):
                QMessageBox.critical(self, "错误", "检测到拓扑环（支流挂接产生循环）。请检查支流与目标河流的关系。")
                return

            # 将支流挂到对应目标（目标可为干流或支流）
            for link in tributary_links:
                name_to_system[link.insertion_river].tributaries.append(link)

            # 生成最终列表（保持界面顺序）
            rivers_final = [name_to_system[grp.get_river_name()]
                            for grp in self.river_groups
                            if grp.get_river_name() in name_to_system]

            config = ReservoirConfig(rivers=rivers_final, data_type=data_type)
            config.save_to_json("project_config.json")

            QMessageBox.information(self, "成功", "配置已保存到 project_config.json")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置时出错：{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ConfigWindow()
    win.show()
    sys.exit(app.exec_())
