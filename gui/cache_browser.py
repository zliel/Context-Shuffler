from aqt import mw
from aqt.qt import *
from aqt.utils import askUser, showInfo
from ..core import cache_manager


class CacheBrowser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Context Shuffler — Cache Browser")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter by card ID or variation text...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Card ID", "Variation"])
        self.table.setColumnWidth(0, 100)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        self.delete_all_btn = QPushButton("Delete All")
        self.delete_all_btn.clicked.connect(self._on_delete_all_clicked)
        btn_layout.addWidget(self.delete_all_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self._on_export_clicked)
        btn_layout.addWidget(self.export_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setDefault(True)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # Enable delete when row selected
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_data(self):
        self.all_data = cache_manager.get_all_variations()
        self._display_data(self.all_data)

    def _display_data(self, data: list[tuple[int, str]]):
        self.table.setRowCount(len(data))
        for row, (card_id, variation) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(str(card_id)))
            self.table.setItem(row, 1, QTableWidgetItem(variation))
            self.table.setRowHeight(
                row, max(40, min(100, variation.count(" ") * 3 + 20))
            )

    def _on_search_changed(self, text: str):
        text_lower = text.lower()
        if not text_lower:
            self._display_data(self.all_data)
            return

        filtered = [
            (cid, var)
            for cid, var in self.all_data
            if text_lower in str(cid).lower() or text_lower in var.lower()
        ]
        self._display_data(filtered)

    def _on_selection_changed(self):
        self.delete_btn.setEnabled(len(self.table.selectedItems()) > 0)

    def _on_delete_clicked(self):
        rows = sorted(
            set(item.row() for item in self.table.selectedItems()), reverse=True
        )
        if not rows:
            return

        if askUser(f"Delete {len(rows)} selected variation(s)?"):
            for row in rows:
                card_id = int(self.table.item(row, 0).text())
                cache_manager.delete_variation(card_id)
            self._load_data()
            showInfo(f"Deleted {len(rows)} variation(s).")

    def _on_delete_all_clicked(self):
        if askUser(
            "Are you sure you want to delete ALL cached variations? This cannot be undone."
        ):
            cache_manager.clear_all_variations()
            self._load_data()
            showInfo("All cached variations have been deleted.")

    def _on_export_clicked(self):
        current_data = []
        for row in range(self.table.rowCount()):
            card_id = self.table.item(row, 0).text()
            variation = self.table.item(row, 1).text()
            current_data.append((card_id, variation))

        if not current_data:
            showInfo("No data to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Cache to CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        import csv

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["card_id", "variation_text"])
            writer.writerows(current_data)

        showInfo(f"Exported {len(current_data)} rows to {path}")


def show_cache_browser(parent=None):
    dialog = CacheBrowser(parent)
    dialog.exec()
