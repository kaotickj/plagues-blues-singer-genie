"""Plague's Blues Singer Genie desktop application."""
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from blues_core import GENDERS, STYLES, Library, Ollama, build_prompt, load_settings, make_names, parse_names, save_settings


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
        self.settings = load_settings()
        self.pool = QThreadPool.globalInstance()
        self.workers = []
        self.setWindowTitle("Plague's Blues Singer Genie · v0.1.0")
        self.resize(1150, 770)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.init_names()
        self.init_studio()
        self.init_library()
        self.init_settings()
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
        self.name_idea = QLineEdit(); self.name_idea.setPlaceholderText("Optional: smoky Chicago club, soul singer, etc.")
        self.ai_names = QComboBox(); self.ai_names.addItems(["Offline generator", "Local Ollama model"])
        form.addRow("Presentation", self.name_gender)
        form.addRow("Blues tradition", self.name_style)
        form.addRow("How many", self.name_count)
        form.addRow("Direction", self.name_idea)
        form.addRow("Engine", self.ai_names)
        layout.addLayout(form)
        controls = QHBoxLayout()
        controls.addWidget(self.button("Generate stage names", self.generate_names))
        controls.addWidget(self.button("Save highlighted artist", self.save_name))
        layout.addLayout(controls)
        self.name_list = QListWidget()
        self.name_list.itemDoubleClicked.connect(lambda _: self.save_name())
        layout.addWidget(self.name_list, 1)
        layout.addWidget(QLabel("Names are creative suggestions. Check artist names and trademarks before publishing."))
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
        form.addRow("Style", self.studio_style)
        form.addRow("Creative brief", self.studio_idea)
        layout.addLayout(form)
        controls = QHBoxLayout()
        controls.addWidget(self.button("Generate with local AI", self.generate_studio))
        controls.addWidget(self.button("Save to library", self.save_draft))
        controls.addWidget(self.button("Save artist biography", self.save_bio))
        layout.addLayout(controls)
        self.studio_output = QTextEdit()
        self.studio_output.setPlaceholderText("Generated material appears here. You can edit it before saving.")
        layout.addWidget(self.studio_output, 1)
        self.tabs.addTab(tab, "Artist & Album Studio")

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
        layout.addWidget(QLabel("Only Ollama text models are used in v0.1. Audio models are not loaded by this application."))
        layout.addWidget(QLabel("Set a remote URL only if you trust that server. Prompts are transmitted to the configured endpoint."))
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
        self.settings = {"url": self.endpoint.text().strip(), "model": self.selected_model()}
        save_settings(self.settings)
        self.statusBar().showMessage("Settings saved")

    def refresh_models(self):
        url = self.endpoint.text().strip()
        def display(models):
            previous = self.selected_model()
            self.model.clear(); self.model.addItems(models)
            if previous in models: self.model.setCurrentText(previous)
            self.connection_status.setText(f"Connected. Found {len(models)} model(s): {', '.join(models) or '(none)'}")
        self.busy(lambda: Ollama(url, timeout=15).models(), display)

    def generate_names(self):
        count = self.name_count.value()
        gender, style, idea = self.name_gender.currentText(), self.name_style.currentText(), self.name_idea.text()
        existing = [a["name"] for a in self.db.artists()]
        if self.ai_names.currentIndex() == 0:
            names = make_names(count, gender, excluded=existing)
            self.populate_names(names)
            return
        prompt = build_prompt("Stage names", style, None, idea, count, gender)
        url, model = self.endpoint.text().strip(), self.selected_model()
        self.busy(lambda: Ollama(url).generate(model, prompt),
                  lambda result: self.populate_names([n for n in parse_names(result, count) if n.casefold() not in {e.casefold() for e in existing}]))

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

    def generate_studio(self):
        task = self.task_pick.currentText()
        prompt = build_prompt(task, self.studio_style.currentText(), self.artist_context(), self.studio_idea.toPlainText())
        url, model = self.endpoint.text().strip(), self.selected_model()
        self.busy(lambda: Ollama(url).generate(model, prompt), self.studio_output.setPlainText)

    def save_draft(self):
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
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
