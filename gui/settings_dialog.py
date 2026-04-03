from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser, tooltip
from ..core import cache_manager
from ..core.providers.ollama import OllamaProvider


TOOLTIPS = {
    "enabled": "Turn the add-on on or off. When disabled, cards will show their original sentence.",
    "target_field": "The name of the card field containing the word or phrase you want to vary (e.g., 'TargetWord'). Must match exactly.",
    "context_field": "The name of the card field containing the example sentence containing the target word (e.g., 'ExampleSentence').\nThis is the field used to populate the generated sentence.",
    "ollama_url": "The URL for your local Ollama API server. Default: http://localhost:11434/api/generate",
    "model": "The Ollama model to use for generating sentence variations. Download models with: ollama pull <model_name>",
    "temperature": "Controls how creative the model is. Lower values (0.1-0.3) produce more predictable variations; higher values (0.7-1.0) produce more diverse, creative output. Defaults to 0.7",
    "keep_alive": "How long to keep the model loaded in memory after each request. Set to 0 for Ollama's default behavior.",
    "system_prompt": "Instructions that guide how the model generates sentences. Be specific about tone, style, or constraints you want.",
    "enabled_decks": "Only apply shuffling to these decks. Leave empty to apply to all decks. One deck name per line.",
    "purge_btn": "Delete all cached sentence variations. Use this after changing the system prompt or model to get fresh variations.",
}


class SettingsDialog(QDialog):
    def __init__(self, addon_name: str, parent=None):
        super().__init__(parent)
        self.addon_name = addon_name
        self.config_data = mw.addonManager.getConfig(addon_name) or {}

        self.setWindowTitle("Context Shuffler Settings")
        self.setMinimumWidth(500)

        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.enabled_check = QCheckBox("Enable Context Shuffler")
        self.enabled_check.setToolTip(TOOLTIPS["enabled"])
        form_layout.addRow(self.enabled_check)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow(line)

        def labeled_field(label_text: str, widget, tooltip_key: str) -> QLabel:
            label = QLabel(label_text)
            label.setToolTip(TOOLTIPS[tooltip_key])
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            form_layout.addRow(label, widget)
            return label

        self.target_edit = QLineEdit()
        self.context_edit = QLineEdit()
        labeled_field("Target Word Field:", self.target_edit, "target_field")
        labeled_field("Context Sentence Field:", self.context_edit, "context_field")

        self.url_edit = QLineEdit()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.0)
        self.temp_spin.setSingleStep(0.1)

        self.keep_alive_spin = QSpinBox()
        self.keep_alive_spin.setRange(0, 60)
        self.keep_alive_spin.setSuffix(" min (0 = use default)")

        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.clicked.connect(self.on_test_connection)

        conn_layout = QHBoxLayout()
        conn_layout.addWidget(self.url_edit)
        conn_layout.addWidget(self.test_conn_btn)

        labeled_field("Ollama API URL:", conn_layout, "ollama_url")
        labeled_field("Model:", self.model_combo, "model")
        labeled_field("Temperature:", self.temp_spin, "temperature")
        labeled_field("Keep Alive:", self.keep_alive_spin, "keep_alive")

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMaximumHeight(80)
        labeled_field("System Prompt:", self.prompt_edit, "system_prompt")

        self.decks_edit = QPlainTextEdit()
        self.decks_edit.setMaximumHeight(80)
        self.decks_edit.setPlaceholderText(
            "One deck name per line. If completely empty, the add-on applies to all decks."
        )
        labeled_field("Enabled Decks:", self.decks_edit, "enabled_decks")

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow(line2)

        self.purge_btn = QPushButton("Purge All Cached Variations")
        self.purge_btn.clicked.connect(self.on_purge_clicked)
        labeled_field("Maintenance:", self.purge_btn, "purge_btn")

        # Standard ok/cancel
        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_box.accepted.connect(self.on_accept)
        self.btn_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(self.btn_box)
        self.setLayout(layout)

    def _load_config(self):
        """Pre-populates the UI slots with Anki's tracked JSON state"""
        self.enabled_check.setChecked(self.config_data.get("enabled", True))
        self.target_edit.setText(self.config_data.get("target_field", "TargetWord"))
        self.context_edit.setText(
            self.config_data.get("context_field", "ExampleSentence")
        )
        self.url_edit.setText(
            self.config_data.get("ollama_url", "http://localhost:11434/api/generate")
        )
        self.temp_spin.setValue(self.config_data.get("temperature", 0.7))
        self.keep_alive_spin.setValue(self.config_data.get("keep_alive", 0))
        self.prompt_edit.setPlainText(self.config_data.get("system_prompt", ""))

        saved_model = self.config_data.get("model", "llama3")
        self._populate_models(saved_model)

        decks = self.config_data.get("enabled_decks", ["Default"])
        self.decks_edit.setPlainText("\n".join(decks))

    def _get_base_url(self) -> str:
        """Extract base URL from the full API URL."""
        url = self.url_edit.text().strip()
        for suffix in ("/api/generate", "/api/chat", "/v1/chat/completions"):
            if url.endswith(suffix):
                return url[: -len(suffix)]
        return url.rstrip("/")

    def _populate_models(self, selected_model: str = ""):
        """Fetch available models from Ollama and populate the dropdown."""
        self.model_combo.clear()
        try:
            base_url = self._get_base_url()
            provider = OllamaProvider(base_url)
            models = provider.list_models()
            if models:
                for model in sorted(models):
                    self.model_combo.addItem(model)
                if selected_model and selected_model in models:
                    self.model_combo.setCurrentText(selected_model)
                else:
                    self.model_combo.setCurrentIndex(0)
            else:
                self.model_combo.addItem("(no models found)")
        except Exception:
            self.model_combo.addItem("(connection failed)")

        if selected_model and self.model_combo.findText(selected_model) == -1:
            self.model_combo.setCurrentText(selected_model)

    def on_test_connection(self):
        """Test the Ollama connection and show results."""
        self.test_conn_btn.setEnabled(False)
        self.test_conn_btn.setText("Testing...")
        QApplication.processEvents()

        try:
            base_url = self._get_base_url()
            provider = OllamaProvider(base_url)
            models = provider.list_models()

            if models:
                showInfo(
                    f"Connection successful!\n\n"
                    f"Found {len(models)} model(s):\n"
                    + "\n".join(f"  - {m}" for m in sorted(models)),
                    title="Test Connection",
                )
                self._populate_models(self.model_combo.currentText())
            else:
                showInfo(
                    "Connected to Ollama, but no models were found.\n\n"
                    "Please pull a model first: ollama pull <model_name>",
                    title="Test Connection",
                )
        except Exception as e:
            showInfo(
                f"Connection failed!\n\n"
                f"Error: {e}\n\n"
                f"Make sure Ollama is running at:\n{self.url_edit.text()}",
                title="Test Connection",
            )
        finally:
            self.test_conn_btn.setEnabled(True)
            self.test_conn_btn.setText("Test Connection")

    def on_purge_clicked(self):
        """Asks for confirmation and then wipes the cache database."""
        if askUser(
            "Are you sure you want to purge all AI-generated variations from the cache? This cannot be undone."
        ):
            cache_manager.clear_all_variations()
            showInfo("Cache database has been cleared.")

    def on_accept(self):
        """Grabs all string inputs and dynamically forces a config overwrite."""
        self.config_data["enabled"] = self.enabled_check.isChecked()
        self.config_data["target_field"] = self.target_edit.text()
        self.config_data["context_field"] = self.context_edit.text()

        url = self.url_edit.text()
        if not url.endswith("/api/generate"):
            url = url.rstrip("/") + "/api/generate"
        self.config_data["ollama_url"] = url

        self.config_data["model"] = self.model_combo.currentText()
        self.config_data["temperature"] = self.temp_spin.value()
        self.config_data["keep_alive"] = self.keep_alive_spin.value()
        self.config_data["system_prompt"] = self.prompt_edit.toPlainText()

        raw_decks = self.decks_edit.toPlainText().split("\n")
        self.config_data["enabled_decks"] = [d.strip() for d in raw_decks if d.strip()]

        mw.addonManager.writeConfig(self.addon_name, self.config_data)
        self.accept()


def show_settings_dialog(addon_name: str) -> None:
    dialog = SettingsDialog(addon_name, parent=mw)
    dialog.exec()
