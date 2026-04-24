from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser, tooltip
from ..core import cache_manager
from ..core.providers import get_provider, PROVIDERS, PROVIDER_NAMES, PROVIDER_ENDPOINTS
import threading


TOOLTIPS = {
    "enabled": "Turn the add-on on or off. When disabled, cards will show their original sentence.",
    "target_field": "The name of the card field containing the word or phrase you want to vary (e.g., 'TargetWord'). Must match exactly.",
    "context_field": "The name of the card field containing the example sentence containing the target word (e.g., 'ExampleSentence').\nThis is the field used to populate the generated sentence.",
    "provider": "Select the LLM provider. Ollama uses its native API; OpenAI-Compatible works with vLLM, LM Studio, llama.cpp, etc.",
    "base_url": "The base URL for your local LLM server.\nOllama default: http://localhost:11434\nLM Studio / llama.cpp default: http://localhost:1234",
    "model": "The model to use for generating sentence variations.\n\nWarning: 'Thinking' models (e.g., Qwen3-30B, DeepSeek-R1) use extra context for reasoning and may need higher max_tokens or will fail to generate.",
    "max_tokens": "Maximum number of tokens to generate. Higher values allow longer responses but take more time. For thinking models, you may need to increase this to 300-500.",
    "temperature": "Controls how creative the model is. Lower values (0.1-0.3) produce more predictable variations; higher values (0.7-1.0) produce more diverse, creative output. Defaults to 0.7",
    "keep_alive": "How long to keep the model loaded in memory after each request. Set to 0 for default behavior.",
    "system_prompt": "Instructions that guide how the model generates sentences. Be specific about tone, style, or constraints you want.",
    "enabled_decks": "Only apply shuffling to these decks. Leave empty to apply to all decks. One deck name per line.",
    "purge_btn": "Delete all cached sentence variations. Use this after changing the system prompt or model to get fresh variations.",
    "refresh_models": "Fetch the list of available models from the server.",
    "shuffling_strategy": "Choose how sentences are shuffled.\n\nAlways: Always show a shuffled sentence.\n\nEase-Based: Shuffle frequency adjusts based on how well you know the card (Hard = less shuffling, Easy = more shuffling).",
    "lapse_recovery_enabled": "When enabled, if you mark a card 'Again', the add-on will show the original sentence for the next few reviews to help re-anchor the primary memory.",
    "lapse_recovery_duration": "Number of reviews to show the original sentence after a lapse before resuming shuffling.",
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

        self.provider_combo = QComboBox()
        for provider_key, provider_name in PROVIDER_NAMES.items():
            self.provider_combo.addItem(provider_name, provider_key)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        labeled_field("Provider:", self.provider_combo, "provider")

        self.base_url_edit = QLineEdit()
        labeled_field("Base URL:", self.base_url_edit, "base_url")

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)

        self.refresh_models_btn = QPushButton("Refresh")
        self.refresh_models_btn.setToolTip(TOOLTIPS["refresh_models"])
        self.refresh_models_btn.clicked.connect(self.on_refresh_models)

        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_combo, 1)
        model_layout.addWidget(self.refresh_models_btn)

        labeled_field("Model:", model_layout, "model")

        self.model_warning_label = QLabel(
            "Warning: Avoid 'thinking' models (e.g., Qwen3-30G, DeepSeek-R1) - they may fail to generate due to high context usage."
        )
        self.model_warning_label.setWordWrap(True)
        self.model_warning_label.setMaximumHeight(40)
        self.model_warning_label.setStyleSheet("color: #cc6600; font-size: 10pt;")
        form_layout.addRow("", self.model_warning_label)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.0)
        self.temp_spin.setSingleStep(0.1)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(50, 4096)
        self.max_tokens_spin.setSingleStep(50)
        self.max_tokens_spin.setValue(150)

        self.keep_alive_spin = QSpinBox()
        self.keep_alive_spin.setRange(0, 60)
        self.keep_alive_spin.setSuffix(" min (0 = use default)")

        labeled_field("Temperature:", self.temp_spin, "temperature")
        labeled_field("Max Tokens:", self.max_tokens_spin, "max_tokens")
        labeled_field("Keep Alive:", self.keep_alive_spin, "keep_alive")

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMaximumHeight(160)
        labeled_field("System Prompt:", self.prompt_edit, "system_prompt")

        self.decks_edit = QPlainTextEdit()
        self.decks_edit.setMaximumHeight(80)
        self.decks_edit.setPlaceholderText(
            "One deck name per line. If completely empty, the add-on applies to all decks."
        )
        labeled_field("Enabled Decks:", self.decks_edit, "enabled_decks")

        # --- Shuffling Strategy Section ---
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow(line2)

        strategy_label = QLabel("<b>Shuffling Strategy</b>")
        form_layout.addRow(strategy_label)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Always Shuffle", "always")
        self.strategy_combo.addItem("Ease-Based Shuffling", "ease-based")
        self.strategy_combo.setToolTip(TOOLTIPS["shuffling_strategy"])
        labeled_field("Strategy:", self.strategy_combo, "shuffling_strategy")

        # --- Lapse Recovery Section ---
        self.lapse_recovery_check = QCheckBox("Enable Lapse Recovery")
        self.lapse_recovery_check.setToolTip(TOOLTIPS["lapse_recovery_enabled"])
        form_layout.addRow(self.lapse_recovery_check)

        self.lapse_duration_spin = QSpinBox()
        self.lapse_duration_spin.setRange(1, 10)
        self.lapse_duration_spin.setValue(3)
        self.lapse_duration_spin.setSuffix(" reviews")
        labeled_field(
            "Recovery Duration:", self.lapse_duration_spin, "lapse_recovery_duration"
        )

        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.HLine)
        line3.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow(line3)

        self.purge_btn = QPushButton("Purge All Cached Variations")
        self.purge_btn.clicked.connect(self.on_purge_clicked)
        labeled_field("Maintenance:", self.purge_btn, "purge_btn")

        self.purge_lapse_btn = QPushButton("Clear Lapse Recovery Data")
        self.purge_lapse_btn.clicked.connect(self.on_purge_lapse_clicked)
        labeled_field("", self.purge_lapse_btn, "purge_btn")

        self.browse_cache_btn = QPushButton("Browse Cache...")
        self.browse_cache_btn.clicked.connect(self._on_browse_cache_clicked)
        labeled_field("", self.browse_cache_btn, "purge_btn")

        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_box.accepted.connect(self.on_accept)
        self.btn_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(self.btn_box)
        self.setLayout(layout)

    def on_purge_lapse_clicked(self):
        """Clears all lapse recovery tracking data."""
        if askUser(
            "Are you sure you want to clear all lapse recovery data? This will resume shuffling for all cards in recovery mode."
        ):
            cache_manager.clear_all_lapse_data()
            showInfo("Lapse recovery data has been cleared.")

    def _on_browse_cache_clicked(self):
        from .cache_browser import show_cache_browser

        show_cache_browser(self, self.addon_name)

    def _get_current_provider_key(self) -> str:
        return self.provider_combo.currentData()

    def _get_current_endpoint(self) -> str:
        provider_key = self._get_current_provider_key()
        return PROVIDER_ENDPOINTS.get(provider_key, "/api/generate")

    def _get_base_url(self) -> str:
        return self.base_url_edit.text().strip().rstrip("/")

    def _get_full_url(self) -> str:
        base = self._get_base_url()
        endpoint = self._get_current_endpoint()
        return f"{base}{endpoint}"

    def on_provider_changed(self):
        provider_key = self._get_current_provider_key()
        from ..core.providers import PROVIDER_DEFAULTS

        default_url = PROVIDER_DEFAULTS.get(provider_key, "http://localhost:11434")
        current_url = self._get_base_url()

        old_default = PROVIDER_DEFAULTS.get("ollama", "http://localhost:11434")
        if current_url == old_default or not current_url:
            self.base_url_edit.setText(default_url)

        self._start_background_model_load()

    def _load_config(self):
        self.enabled_check.setChecked(self.config_data.get("enabled", True))
        self.target_edit.setText(self.config_data.get("target_field", "TargetWord"))
        self.context_edit.setText(
            self.config_data.get("context_field", "ExampleSentence")
        )

        provider = self.config_data.get("provider", "ollama")
        provider_index = self.provider_combo.findData(provider)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)

        self.base_url_edit.setText(
            self.config_data.get("base_url", "http://localhost:11434")
        )

        self.temp_spin.setValue(self.config_data.get("temperature", 0.7))
        self.max_tokens_spin.setValue(self.config_data.get("max_tokens", 150))
        self.keep_alive_spin.setValue(self.config_data.get("keep_alive", 0))
        self.prompt_edit.setPlainText(self.config_data.get("system_prompt", ""))

        saved_model = self.config_data.get("model", "llama3")
        self.model_combo.setCurrentText(saved_model)

        decks = self.config_data.get("enabled_decks", [])
        self.decks_edit.setPlainText("\n".join(decks))

        strategy = self.config_data.get("shuffling_strategy", "always")
        strategy_index = self.strategy_combo.findData(strategy)
        if strategy_index >= 0:
            self.strategy_combo.setCurrentIndex(strategy_index)

        self.lapse_recovery_check.setChecked(
            self.config_data.get("lapse_recovery_enabled", True)
        )
        self.lapse_duration_spin.setValue(
            self.config_data.get("lapse_recovery_duration", 3)
        )

        self._start_background_model_load()

    def _start_background_model_load(self):
        self.model_combo.clear()
        self.model_combo.addItem("(loading models...)")

        base_url = self._get_base_url()
        provider_key = self._get_current_provider_key()
        saved_model = self.config_data.get("model", "")

        def background_load():
            try:
                provider = get_provider(provider_key, base_url)
                models = provider.list_models()
                mw.taskman.run_on_main(
                    lambda: self._on_models_loaded(models, saved_model)
                )
            except Exception:
                mw.taskman.run_on_main(
                    lambda: self._on_models_loaded([], saved_model, error=True)
                )

        thread = threading.Thread(target=background_load, daemon=True)
        thread.start()

    def _on_models_loaded(self, models: list, selected_model: str, error: bool = False):
        self.model_combo.clear()
        if error or not models:
            self.model_combo.addItem("(connection failed)")
            if selected_model:
                self.model_combo.setCurrentText(selected_model)
        else:
            for model in sorted(models):
                self.model_combo.addItem(model)
            if selected_model and selected_model in models:
                self.model_combo.setCurrentText(selected_model)
            elif models:
                self.model_combo.setCurrentIndex(0)

    def _populate_models(self, selected_model: str = ""):
        self.model_combo.clear()
        try:
            base_url = self._get_base_url()
            provider_key = self._get_current_provider_key()
            provider = get_provider(provider_key, base_url)
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

    def on_refresh_models(self):
        self._populate_models(self.model_combo.currentText())

    def on_purge_clicked(self):
        if askUser(
            "Are you sure you want to purge all AI-generated variations from the cache? This cannot be undone."
        ):
            cache_manager.clear_all_variations()
            showInfo("Cache database has been cleared.")

    def on_accept(self):
        self.config_data["enabled"] = self.enabled_check.isChecked()
        self.config_data["target_field"] = self.target_edit.text()
        self.config_data["context_field"] = self.context_edit.text()

        self.config_data["provider"] = self._get_current_provider_key()
        self.config_data["base_url"] = self._get_base_url()
        self.config_data["url"] = self._get_full_url()

        self.config_data["model"] = self.model_combo.currentText()
        self.config_data["temperature"] = self.temp_spin.value()
        self.config_data["max_tokens"] = self.max_tokens_spin.value()
        self.config_data["keep_alive"] = self.keep_alive_spin.value()
        self.config_data["system_prompt"] = self.prompt_edit.toPlainText()

        raw_decks = self.decks_edit.toPlainText().split("\n")
        self.config_data["enabled_decks"] = [d.strip() for d in raw_decks if d.strip()]

        self.config_data["shuffling_strategy"] = self.strategy_combo.currentData()
        self.config_data["lapse_recovery_enabled"] = (
            self.lapse_recovery_check.isChecked()
        )
        self.config_data["lapse_recovery_duration"] = self.lapse_duration_spin.value()

        mw.addonManager.writeConfig(self.addon_name, self.config_data)
        self.accept()


def show_settings_dialog(addon_name: str) -> None:
    dialog = SettingsDialog(addon_name, parent=mw)
    dialog.exec()
