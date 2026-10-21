"""Plague's Music Studio, local-first multi-genre creation suite."""
import sys
import hashlib
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QFileDialog, QCheckBox,
)

from blues_core import STYLES, Library, Ollama, load_settings, save_settings, paths
from name_engine import NameBank, GENDERS, KINDS
from model_manager import (ManagedRuntime, app_models_dir, known_executables, known_model_stores,
                           executable_version, install_managed_runtime, import_local_gguf,
                           pull_model, verify_model)
from curation import ROLES, run_curation
from suno import SunoPackage, export_suno
from music_engine import FORMATS, MusicConfig, generate_song, verify_ace, check_tool
from genre_presets import make_variation, variation_prompt, canonical_genre, is_metal



class Signals(QObject):
    done = pyqtSignal(object)
    error = pyqtSignal(str)


class Work(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = Signals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as exc:
            self.signals.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Library()
        self.name_bank = NameBank(self.db.location)
        self.managed_runtime = ManagedRuntime()
        self.suno_package = None
        self.song_approved = False
        self.reviewed_song_digest = None
        self.pending_variation = None
        self.active_variation = None
        self.settings = load_settings()
        self.pool = QThreadPool.globalInstance()
        self.workers = []
        self.setWindowTitle("Plague's Music Studio · v0.3.0")
        self.resize(1150, 770)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.init_names()
        self.init_studio()
        self.init_library()
        self.init_settings()
        self.init_word_bank()
        self.init_model_manager()
        self.init_audio()
        self.refresh_artists()
        self.statusBar().showMessage("Offline name generation is ready. Connect Ollama in Settings for AI.")

    def panel(self):
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        return outer, layout

    def button(self, caption, action):
        b = QPushButton(caption)
        b.clicked.connect(action)
        return b

    def init_names(self):
        tab, layout = self.panel()
        form = QFormLayout()
        self.name_gender = QComboBox(); self.name_gender.addItems(GENDERS)
        self.name_style = QComboBox(); self.name_style.addItems(STYLES)
        self.name_count = QSpinBox(); self.name_count.setRange(1, 50); self.name_count.setValue(10)
        self.name_idea = QLineEdit(); self.name_idea.setPlaceholderText("Optional: blues or metal persona, band or stage nickname")
        form.addRow("Presentation", self.name_gender)
        form.addRow("Artist genre", self.name_style)
        form.addRow("How many", self.name_count)
        form.addRow("Direction", self.name_idea)
        layout.addLayout(form)
        controls = QHBoxLayout()
        controls.addWidget(self.button("Generate stage names", self.generate_names))
        controls.addWidget(self.button("Save highlighted artist", self.save_name))
        layout.addLayout(controls)
        self.name_list = QListWidget()
        self.name_list.itemDoubleClicked.connect(lambda _: self.save_name())
        layout.addWidget(self.name_list, 1)
        layout.addWidget(QLabel("Database permutations, no AI required. Edit prefixes, surnames, nicknames, bands and name patterns in Word Bank."))
        layout.addWidget(QLabel("Names are suggestions: check stage names and trademarks before publishing."))
        self.tabs.addTab(tab, "Stage Name Lab")

    def init_studio(self):
        tab, layout = self.panel()
        form = QFormLayout()
        self.artist_pick = QComboBox()
        self.task_pick = QComboBox(); self.task_pick.addItems([
            "Artist biography", "Artist style guide", "Album concept", "Three album concepts",
            "Song lyrics", "Suno style prompt", "Website promo",
        ])
        self.studio_style = QComboBox(); self.studio_style.addItems(STYLES)
        self.studio_idea = QTextEdit()
        self.studio_idea.setMaximumHeight(90)
        self.studio_idea.setPlaceholderText("Themes, hometown, attitude, narrative, lyrical subject, album direction...")
        form.addRow("Artist", self.artist_pick)
        form.addRow("Create", self.task_pick)
        form.addRow("Genre / Style", self.studio_style)
        form.addRow("Creative brief", self.studio_idea)
        layout.addLayout(form)
        layout.addWidget(QLabel("Creative variation, independent choices for this song rather than a fixed genre template:"))
        self.variation_preview = QTextEdit()
        self.variation_preview.setReadOnly(True)
        self.variation_preview.setMaximumHeight(116)
        self.variation_preview.setPlaceholderText("Click Shuffle Creative Direction to preview distinct choices.")
        layout.addWidget(self.variation_preview)
        layout.addWidget(self.button("Shuffle creative direction", self.shuffle_variation))
        self.studio_style.currentTextChanged.connect(self.clear_variation)
        self.studio_style.currentTextChanged.connect(self.apply_genre_audio_defaults)
        controls = QHBoxLayout()
        controls.addWidget(self.button("Generate with local AI", self.generate_studio))
        controls.addWidget(self.button("Save to library", self.save_draft))
        controls.addWidget(self.button("Save artist biography", self.save_bio))
        layout.addLayout(controls)
        self.review_status = QLabel("Curation: select models for Research, Draft, Edit and Audit in AI Settings.")
        self.review_status.setWordWrap(True)
        layout.addWidget(self.review_status)
        self.studio_output = QTextEdit()
        self.studio_output.setPlaceholderText("Curated output appears here. Edit before saving.")
        layout.addWidget(self.studio_output, 1)
        layout.addWidget(QLabel("For songs: Suno Custom Mode has separate Lyrics, Style of Music and Exclude fields."))
        self.suno_tabs = QTabWidget()
        self.lyrics_output = QTextEdit()
        self.style_output = QTextEdit()
        self.exclude_output = QTextEdit()
        for name, field in (("Tagged Lyrics", self.lyrics_output), ("Style Prompt", self.style_output), ("Exclude Styles", self.exclude_output)):
            self.suno_tabs.addTab(field, name)
        self.suno_tabs.setMaximumHeight(245)
        layout.addWidget(self.suno_tabs)
        copy_controls = QHBoxLayout()
        copy_controls.addWidget(self.button("Copy lyrics", lambda: QApplication.clipboard().setText(self.lyrics_output.toPlainText())))
        copy_controls.addWidget(self.button("Copy style", lambda: QApplication.clipboard().setText(self.style_output.toPlainText())))
        copy_controls.addWidget(self.button("Copy excludes", lambda: QApplication.clipboard().setText(self.exclude_output.toPlainText())))
        layout.addLayout(copy_controls)
        self.tabs.addTab(tab, "Songwriting & Albums")

    def init_library(self):
        tab, layout = self.panel()
        split = QSplitter(Qt.Orientation.Horizontal)
        self.library_list = QListWidget()
        self.library_list.currentRowChanged.connect(self.show_library_entry)
        self.library_content = QTextEdit()
        self.library_content.setReadOnly(True)
        split.addWidget(self.library_list); split.addWidget(self.library_content)
        split.setStretchFactor(1, 2)
        layout.addWidget(self.button("Refresh library", self.refresh_library))
        layout.addWidget(split, 1)
        self.tabs.addTab(tab, "Library")

    def init_settings(self):
        tab, layout = self.panel()
        form = QFormLayout()
        self.endpoint = QLineEdit(self.settings["url"])
        self.model = QComboBox(); self.model.setEditable(True)
        self.model.setCurrentText(self.settings.get("model", ""))
        form.addRow("Ollama server URL", self.endpoint)
        form.addRow("Text generation model", self.model)
        layout.addLayout(form)
        layout.addWidget(self.button("Discover installed Ollama models", self.refresh_models))
        layout.addWidget(self.button("Save settings", self.persist_settings))
        self.connection_status = QLabel("Click Discover to query /api/tags. Model files alone do not confirm availability.")
        self.connection_status.setWordWrap(True)
        layout.addWidget(self.connection_status)
        layout.addWidget(QLabel("Ollama is used for curated text. ACE-Step is configured separately in Music Production."))
        layout.addWidget(QLabel("For your Goodneighbor Linux server, use an SSH tunnel to its loopback Ollama port, not the Windows PC model paths."))
        layout.addWidget(QLabel("Prompts are sent to the configured endpoint. Do not expose Ollama directly to the internet."))
        self.role_models = {}
        for role in ROLES:
            selector = QComboBox(); selector.setEditable(True)
            selector.setCurrentText(self.settings.get("roles", {}).get(role, self.settings.get("model", "")))
            self.role_models[role] = selector
            form.addRow(role.capitalize() + " model", selector)
        self.threshold = QSpinBox(); self.threshold.setRange(50, 100); self.threshold.setValue(int(self.settings.get("threshold", 85)))
        self.max_rewrites = QSpinBox(); self.max_rewrites.setRange(0, 3); self.max_rewrites.setValue(int(self.settings.get("max_rewrites", 2)))
        form.addRow("Minimum audit score", self.threshold)
        form.addRow("Maximum rewrites", self.max_rewrites)
        layout.addStretch()
        self.tabs.addTab(tab, "AI Settings")

    def busy(self, work, callback):
        worker = Work(work)
        worker.signals.done.connect(lambda output: (self.statusBar().showMessage("Ready"), callback(output), self.workers.remove(worker)))
        worker.signals.error.connect(lambda err: (self.statusBar().showMessage("Error"), QMessageBox.warning(self, "Generation failed", err), self.workers.remove(worker)))
        self.workers.append(worker)
        self.statusBar().showMessage("Working with the local model...")
        self.pool.start(worker)

    def selected_model(self):
        return self.model.currentText().strip()

    def persist_settings(self):
        self.settings = {"url": self.endpoint.text().strip(), "model": self.selected_model(),
                         "roles": {role: selector.currentText().strip() for role, selector in self.role_models.items()},
                         "threshold": self.threshold.value(), "max_rewrites": self.max_rewrites.value()}
        save_settings(self.settings)
        self.statusBar().showMessage("Settings saved")

    def refresh_models(self):
        url = self.endpoint.text().strip()
        def display(models):
            previous = self.selected_model()
            self.model.clear(); self.model.addItems(models)
            if previous: self.model.setCurrentText(previous)
            for role, combo in self.role_models.items():
                existing = combo.currentText()
                combo.clear(); combo.addItems(models)
                if existing: combo.setCurrentText(existing)
                elif models: combo.setCurrentText(models[0])
            self.connection_status.setText(f"Connected. Found {len(models)} model(s): {', '.join(models) or '(none)'}")
        self.busy(lambda: Ollama(url, timeout=15).models(), display)

    def generate_names(self):
        try:
            existing = [a["name"] for a in self.db.artists()]
            names = self.name_bank.generate(self.name_count.value(), self.name_gender.currentText(),
                                            self.name_style.currentText(), excluded=existing)
            self.populate_names(names)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Name generator", str(exc))

    def populate_names(self, names):
        self.name_list.clear(); self.name_list.addItems(names)
        self.statusBar().showMessage(f"Generated {len(names)} unique suggestions")

    def save_name(self):
        item = self.name_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Select a name", "Highlight a name first."); return
        self.db.add_artist(item.text(), self.name_style.currentText())
        self.refresh_artists()
        self.statusBar().showMessage(f"Saved {item.text()}")

    def refresh_artists(self):
        previous = self.artist_pick.currentData() if self.artist_pick.count() else None
        self.artist_pick.clear(); self.artist_pick.addItem("(No artist, standalone concept)", None)
        for artist in self.db.artists():
            self.artist_pick.addItem(artist["name"], artist["id"])
        index = self.artist_pick.findData(previous)
        self.artist_pick.setCurrentIndex(index if index >= 0 else 0)
        self.refresh_library()

    def artist_context(self):
        artist_id = self.artist_pick.currentData()
        return next((a for a in self.db.artists() if a["id"] == artist_id), None)

    def clear_variation(self, _=None):
        self.pending_variation = None
        self.variation_preview.clear()

    def shuffle_variation(self):
        genre = self.studio_style.currentText()
        artist = self.artist_context()
        artist_id = artist['id'] if artist else None
        recent = self.db.recent_variations(genre, artist_id)
        self.pending_variation = make_variation(genre, recent)
        self.variation_preview.setPlainText(variation_prompt(self.pending_variation))

    def apply_genre_audio_defaults(self, style):
        # These widgets are initialized after Studio; early signals must be ignored.
        if hasattr(self, 'audio_scale'):
            self.audio_scale.setCurrentText('minor' if is_metal(style) else 'major')

    def generate_studio(self):
        task = self.task_pick.currentText()
        style = self.studio_style.currentText()
        idea = self.studio_idea.toPlainText()
        artist = self.artist_context()
        artist_id = artist['id'] if artist else None
        url = self.endpoint.text().strip()
        roles = {role: widget.currentText().strip() for role, widget in self.role_models.items()}
        threshold, attempts = self.threshold.value(), self.max_rewrites.value()
        plan = self.pending_variation or make_variation(style, self.db.recent_variations(style, artist_id))
        self.pending_variation = None
        self.active_variation = (style, artist_id, plan)
        self.variation_preview.setPlainText(variation_prompt(plan))
        self.review_status.setText("Curation in progress. Research → Draft → Edit → Independent Audit.")
        self.song_approved = False
        self.reviewed_song_digest = None
        self.suno_package = None
        self.busy(lambda: run_curation(task, style, artist, idea, url, roles,
                                      threshold=threshold, max_rewrites=attempts, variation=plan), self.display_curated)

    def display_curated(self, result):
        if self.active_variation:
            style, artist_id, plan = self.active_variation
            self.db.record_variation(style, artist_id, plan)
            self.active_variation = None
        status = "APPROVED" if result.approved else "NEEDS REVISION"
        self.review_status.setText(f"{status}, score {result.score}/100. {result.feedback}")
        self.studio_output.setPlainText(result.content)
        if result.suno:
            self.suno_package = result.suno
            self.song_approved = bool(result.approved)
            self.reviewed_song_digest = hashlib.sha256(export_suno(result.suno).encode("utf-8")).hexdigest()
            self.lyrics_output.setPlainText(result.suno.lyrics)
            self.style_output.setPlainText(result.suno.style)
            self.exclude_output.setPlainText(result.suno.exclude_styles)
        else:
            self.lyrics_output.clear(); self.style_output.clear(); self.exclude_output.clear()

    def save_draft(self):
        if self.task_pick.currentText() == "Song lyrics" and self.suno_package:
            body = export_suno(self.current_suno())
        else:
            body = self.studio_output.toPlainText().strip()
        if not body:
            QMessageBox.information(self, "Nothing to save", "Generate or write some content first."); return
        self.db.add_draft(self.artist_pick.currentData(), self.task_pick.currentText(), body)
        self.refresh_library()
        self.statusBar().showMessage("Draft saved")

    def save_bio(self):
        artist_id = self.artist_pick.currentData()
        if not artist_id:
            QMessageBox.information(self, "Select artist", "Select a saved artist first."); return
        text = self.studio_output.toPlainText().strip()
        if not text:
            return
        self.db.set_bio(artist_id, text)
        self.refresh_library()
        self.statusBar().showMessage("Artist biography updated")

    def refresh_library(self):
        self.entries = []
        self.library_list.clear()
        for artist in self.db.artists():
            self.library_list.addItem("ARTIST  ·  " + artist["name"])
            self.entries.append(f"{artist['name']}\nStyle: {artist['style']}\n\n{artist['bio']}")
        for draft in self.db.drafts():
            self.library_list.addItem(f"DRAFT  ·  {draft['task']} · #{draft['id']}")
            self.entries.append(draft["content"])

    def current_suno(self):
        original = self.suno_package
        if original is None:
            raise ValueError("Generate curated lyrics first")
        return SunoPackage(title=original.title, lyrics=self.lyrics_output.toPlainText(),
                           style=self.style_output.toPlainText(), exclude_styles=self.exclude_output.toPlainText())

    def init_word_bank(self):
        tab, layout = self.panel()
        layout.addWidget(QLabel("Edit weighted stage-name components for both blues and metal: first names, nicknames, prefixes, surnames, suffixes and bands."))
        form = QFormLayout()
        self.part_kind = QComboBox(); self.part_kind.addItems(KINDS)
        self.part_value = QLineEdit(); self.part_value.setPlaceholderText("e.g. Blue River")
        self.part_gender = QComboBox(); self.part_gender.addItems(GENDERS)
        self.part_style = QComboBox(); self.part_style.addItems(("Any", *STYLES))
        self.part_weight = QSpinBox(); self.part_weight.setRange(1, 20); self.part_weight.setValue(1)
        for title, w in (("Component type", self.part_kind), ("Text", self.part_value),
                         ("Presentation", self.part_gender), ("Blues tradition", self.part_style), ("Weight", self.part_weight)):
            form.addRow(title, w)
        layout.addLayout(form)
        controls = QHBoxLayout()
        controls.addWidget(self.button("Add component", self.add_component))
        controls.addWidget(self.button("Remove selected component", self.remove_component))
        layout.addLayout(controls)
        self.part_list = QListWidget(); layout.addWidget(self.part_list, 1)
        self.pattern_value = QLineEdit(); self.pattern_value.setPlaceholderText('{prefix} {first} "{nickname}" {last}')
        layout.addWidget(self.pattern_value)
        controls = QHBoxLayout()
        controls.addWidget(self.button("Add name pattern", self.add_pattern))
        controls.addWidget(self.button("Remove selected pattern", self.remove_pattern))
        layout.addLayout(controls)
        self.pattern_list = QListWidget(); layout.addWidget(self.pattern_list, 1)
        self.part_kind.currentIndexChanged.connect(self.refresh_word_bank)
        self.refresh_word_bank()
        self.tabs.addTab(tab, "Word Bank")

    def refresh_word_bank(self, *_):
        self.part_list.clear()
        for item in self.name_bank.parts(self.part_kind.currentText()):
            text = f"{item['value']}  ·  {item['gender']} / {item['style']}  ·  weight {item['weight']}"
            self.part_list.addItem(text)
            self.part_list.item(self.part_list.count()-1).setData(Qt.ItemDataRole.UserRole, item['id'])
        self.pattern_list.clear()
        for item in self.name_bank.patterns():
            self.pattern_list.addItem(f"{item['pattern']}  ·  weight {item['weight']}")
            self.pattern_list.item(self.pattern_list.count()-1).setData(Qt.ItemDataRole.UserRole, item['id'])

    def add_component(self):
        try:
            self.name_bank.add(self.part_kind.currentText(), self.part_value.text(),
                               self.part_gender.currentText(), self.part_style.currentText(), self.part_weight.value())
            self.part_value.clear(); self.refresh_word_bank()
        except Exception as exc:
            QMessageBox.warning(self, "Component", str(exc))

    def remove_component(self):
        item = self.part_list.currentItem()
        if item and QMessageBox.question(self, "Remove word", "Delete this name component?") == QMessageBox.StandardButton.Yes:
            self.name_bank.remove(item.data(Qt.ItemDataRole.UserRole)); self.refresh_word_bank()

    def add_pattern(self):
        try:
            self.name_bank.add_pattern(self.pattern_value.text())
            self.pattern_value.clear(); self.refresh_word_bank()
        except Exception as exc:
            QMessageBox.warning(self, "Name pattern", str(exc))

    def remove_pattern(self):
        item = self.pattern_list.currentItem()
        if item and QMessageBox.question(self, "Remove pattern", "Delete this name template?") == QMessageBox.StandardButton.Yes:
            self.name_bank.remove_pattern(item.data(Qt.ItemDataRole.UserRole)); self.refresh_word_bank()

    def init_model_manager(self):
        tab, layout = self.panel()
        layout.addWidget(QLabel("Locate, verify, install and use existing or brand-new Ollama installations and GGUF models."))
        self.runtime_list = QListWidget(); self.runtime_list.setMaximumHeight(125); layout.addWidget(self.runtime_list)
        self.stores_list = QListWidget(); self.stores_list.setMaximumHeight(105); layout.addWidget(self.stores_list)
        buttons = QHBoxLayout()
        buttons.addWidget(self.button("Locate runtimes and model stores", self.locate_models))
        buttons.addWidget(self.button("Install verified Ollama (user space)", self.install_ollama))
        layout.addLayout(buttons)
        buttons = QHBoxLayout()
        buttons.addWidget(self.button("Start private managed Ollama", self.start_ollama))
        buttons.addWidget(self.button("Stop managed Ollama", self.stop_ollama))
        layout.addLayout(buttons)
        form = QFormLayout()
        self.pull_name = QLineEdit(); self.pull_name.setPlaceholderText("e.g. qwen3:4b or gemma3:4b")
        self.gguf_path = QLineEdit(); self.gguf_path.setPlaceholderText("Existing GGUF file on this computer")
        self.import_name = QLineEdit(); self.import_name.setPlaceholderText("Name for imported GGUF model")
        form.addRow("Model to download", self.pull_name)
        form.addRow("Local GGUF file", self.gguf_path)
        form.addRow("Import as", self.import_name)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addWidget(self.button("Download model", self.pull_new_model))
        buttons.addWidget(self.button("Verify selected model", self.verify_selected_model))
        buttons.addWidget(self.button("Browse GGUF...", self.pick_gguf))
        buttons.addWidget(self.button("Import GGUF", self.import_gguf))
        layout.addLayout(buttons)
        self.runtime_log = QTextEdit(); self.runtime_log.setReadOnly(True); layout.addWidget(self.runtime_log)
        layout.addWidget(QLabel("App-managed Ollama runs on loopback port 11535, with its own model store. It never replaces system Ollama."))
        self.tabs.addTab(tab, "Model Manager")
        self.locate_models()

    def log_manager(self, message):
        self.runtime_log.append(str(message))

    def locate_models(self):
        self.runtime_list.clear(); self.stores_list.clear()
        for p in known_executables():
            self.runtime_list.addItem(str(p))
        for item in known_model_stores():
            self.stores_list.addItem(item['path'] + ('  (Ollama store)' if item['ollama_store'] else ''))
        self.log_manager(f"Found {self.runtime_list.count()} Ollama executable(s), {self.stores_list.count()} model store(s).")

    def install_ollama(self):
        if QMessageBox.question(self, "Install Ollama", "Download the official SHA-256-verified Ollama runtime to your user account? It may exceed 1 GB.") != QMessageBox.StandardButton.Yes:
            return
        self.busy(lambda: install_managed_runtime(), lambda path: (self.log_manager('Installed at '+path), self.locate_models()))

    def selected_executable(self):
        item = self.runtime_list.currentItem()
        return item.text() if item else (str(known_executables()[0]) if known_executables() else '')

    def start_ollama(self):
        exe = self.selected_executable()
        if not exe:
            QMessageBox.information(self,"No Ollama", "Install or locate an Ollama executable first."); return
        def ready(url):
            self.endpoint.setText(url); self.log_manager('Managed runtime running at '+url); self.refresh_models()
        self.busy(lambda: self.managed_runtime.start(exe), ready)

    def stop_ollama(self):
        self.managed_runtime.stop(); self.log_manager('Managed runtime stopped.')

    def pull_new_model(self):
        name = self.pull_name.text().strip()
        url = self.endpoint.text().strip()
        if not name or QMessageBox.question(self,"Download model",f"Download {name} into the selected Ollama server's model store? (Model size may be large)") != QMessageBox.StandardButton.Yes:
            return
        self.busy(lambda: pull_model(url,name), lambda models: (self.log_manager('Downloaded '+name),self.refresh_models()))

    def verify_selected_model(self):
        self.busy(lambda: verify_model(self.endpoint.text().strip(),self.selected_model()),
                  lambda result: self.log_manager('Verified model: '+str(result)))

    def pick_gguf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Locate a GGUF model", str(Path.home()), "GGUF Models (*.gguf)")
        if path: self.gguf_path.setText(path)

    def import_gguf(self):
        exe = self.selected_executable()
        if not exe:
            QMessageBox.warning(self,"No Ollama", "Locate Ollama first."); return
        url=self.endpoint.text().strip(); src=self.gguf_path.text().strip(); name=self.import_name.text().strip()
        if QMessageBox.question(self,"Import model",f"Import {Path(src).name} as {name} into the selected Ollama instance?") != QMessageBox.StandardButton.Yes:
            return
        self.busy(lambda: import_local_gguf(url,exe,src,name),
                  lambda info: (self.log_manager('Imported '+str(info)),self.refresh_models()))

    def init_audio(self):
        tab,layout=self.panel()
        layout.addWidget(QLabel("Produce an approved Suno-ready song using ACE-Step 1.5. Use the Goodneighbor Linux server via a private SSH tunnel, or local Vulkan CLI binaries."))
        form=QFormLayout()
        self.ace_mode=QComboBox(); self.ace_mode.addItems(["server","cli"])
        self.ace_url=QLineEdit("http://127.0.0.1:8080")
        self.ace_lm=QLineEdit("/opt/gnb-song-audio/ace-lm")
        self.ace_synth=QLineEdit("/opt/gnb-song-audio/ace-synth")
        self.ace_models=QLineEdit("/var/lib/gnb-song-audio/models")
        self.ace_device=QLineEdit("Vulkan0")
        self.audio_bpm=QSpinBox(); self.audio_bpm.setRange(45,260); self.audio_bpm.setValue(72)
        self.audio_seconds=QSpinBox(); self.audio_seconds.setRange(30,600); self.audio_seconds.setValue(210)
        self.audio_key=QComboBox(); self.audio_key.addItems(["E","A","G","C","D","F","B"])
        self.audio_scale=QComboBox(); self.audio_scale.addItems(["major","minor"])
        self.audio_scale.setCurrentText('major')
        self.audio_format=QComboBox(); self.audio_format.addItems(FORMATS.keys())
        self.audio_folder=QLineEdit(str(paths()/"rendered-songs"))
        self.ffmpeg_path=QLineEdit("ffmpeg")
        self.ffprobe_path=QLineEdit("ffprobe")
        for title,w in (("Backend",self.ace_mode),("ACE API (local SSH tunnel)",self.ace_url),
                       ("ACE language binary",self.ace_lm),("ACE synthesis binary",self.ace_synth),
                       ("ACE model directory",self.ace_models),("GPU device",self.ace_device),
                       ("BPM",self.audio_bpm),("Duration seconds",self.audio_seconds),
                       ("Key",self.audio_key),("Scale",self.audio_scale),("Export format",self.audio_format),
                       ("Output directory",self.audio_folder),("FFmpeg",self.ffmpeg_path),
                       ("FFprobe",self.ffprobe_path)):
            form.addRow(title,w)
        layout.addLayout(form)
        buttons=QHBoxLayout()
        buttons.addWidget(self.button("Browse output directory", self.browse_audio_folder))
        buttons.addWidget(self.button("Verify ACE-Step + FFmpeg", self.verify_audio))
        buttons.addWidget(self.button("Generate full song", self.render_audio))
        layout.addLayout(buttons)
        self.audio_log=QTextEdit(); self.audio_log.setReadOnly(True); self.audio_log.setMaximumHeight(145)
        layout.addWidget(self.audio_log)
        self.tabs.addTab(tab,"Music Production")

    def browse_audio_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Choose music output directory",self.audio_folder.text())
        if folder: self.audio_folder.setText(folder)

    def music_config(self):
        return MusicConfig(mode=self.ace_mode.currentText(),server_url=self.ace_url.text().strip(),
            lm_executable=self.ace_lm.text().strip(),synth_executable=self.ace_synth.text().strip(),
            model_dir=self.ace_models.text().strip(),device=self.ace_device.text().strip(),
            bpm=self.audio_bpm.value(),seconds=self.audio_seconds.value(),key=self.audio_key.currentText(),scale=self.audio_scale.currentText(),
            output_format=self.audio_format.currentText(),ffmpeg=self.ffmpeg_path.text().strip(),
            ffprobe=self.ffprobe_path.text().strip())

    def verify_audio(self):
        conf=self.music_config()
        self.busy(lambda: (verify_ace(conf),check_tool(conf.ffmpeg),check_tool(conf.ffprobe)),
                  lambda result: self.audio_log.append('Verified: '+str(result)))

    def render_audio(self):
        if self.task_pick.currentText() != "Song lyrics" or not self.song_approved:
            QMessageBox.warning(self,"Curation required","Select Song lyrics and pass the independent lyric audit first.")
            return
        pkg = self.current_suno()
        if hashlib.sha256(export_suno(pkg).encode("utf-8")).hexdigest() != self.reviewed_song_digest:
            QMessageBox.warning(self, "Review required", "The Suno lyrics or style fields have changed since the approved audit. Generate and audit a new version before audio production.")
            return
        conf = self.music_config()
        folder = self.audio_folder.text().strip()
        self.audio_log.append('Starting ACE-Step job using approved lyrics and genre-specific style. Music and vocals are generated together.')
        self.busy(lambda: generate_song(pkg,conf,folder), lambda result: self.audio_log.append('Finished: '+str(result)))

    def closeEvent(self, event):
        self.managed_runtime.stop()
        self.name_bank.close()
        super().closeEvent(event)

    def show_library_entry(self, index):
        self.library_content.setPlainText(self.entries[index] if 0 <= index < len(self.entries) else "")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background: #171b22; color: #f0eadf; font-size: 15px; }
        QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox {
            background: #242c35; color: #fff5e5; border: 1px solid #5b6875;
            border-radius: 5px; padding: 7px; selection-background-color: #a26b38;
        }
        QPushButton { background: #a86d36; color: #151515; font-weight: bold;
                      border-radius: 5px; padding: 10px; }
        QPushButton:hover { background: #cf9756; }
        QTabBar::tab { background: #303843; padding: 12px 18px; margin-right: 4px; }
        QTabBar::tab:selected { background: #a86d36; color: #111; }
    """)
    window = MainWindow()
    if "--smoke-test" in sys.argv:
        window.close()
        return
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
