"""Offscreen integration tests for actual model-manager UI action wiring."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class GuiIntegrationTests(unittest.TestCase):
    def test_name_generator_and_existing_model_store(self):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            from main import MainWindow
        except ImportError as error:
            self.skipTest('PyQt6 not installed: '+str(error))
        app=QApplication.instance() or QApplication(['model-manager-test'])
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'existing-ollama-models'
            manifest=path/'manifests'/'registry.ollama.ai'/'library'/'qwen3'/'4b'
            manifest.parent.mkdir(parents=True,exist_ok=True)
            manifest.write_text('{}')
            with patch.dict(os.environ,{'LOCALAPPDATA':td}):
                window=MainWindow()
                try:
                    window.generate_names()
                    self.assertEqual(window.name_list.count(),10)
                    window.extra_model_paths=[str(path)]
                    window.locate_models(str(path))
                    self.assertEqual(window.chosen_store(),str(path))
                    self.assertIn('qwen3:4b',[window.model.itemText(i) for i in range(window.model.count())])
                    called=[]
                    def synchronous_busy(fn,done,**kwargs):
                        done(fn())
                    with patch.object(window,'selected_executable',return_value='/some/ollama'), \
                         patch.object(window.managed_runtime,'start',side_effect=lambda exe,store: called.append((exe,store)) or 'http://127.0.0.1:11535'), \
                         patch.object(window,'busy',side_effect=synchronous_busy), \
                         patch.object(window,'refresh_models'):
                        window.start_ollama()
                    self.assertEqual(called,[('/some/ollama',str(path))])
                    self.assertEqual(window.endpoint.text(),'http://127.0.0.1:11535')
                finally:
                    window.close()
        app.processEvents()


if __name__=='__main__':
    unittest.main()
