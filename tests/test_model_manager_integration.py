"""Model-manager integration regressions independent of a live GPU or network."""
import io
import os
import sys
import hashlib
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import model_manager as m


class FakeZstd:
    class ZstdDecompressor:
        def stream_reader(self, stream):
            return stream


def fake_archive(link='../bin/ollama'):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w') as tar:
        data=b'#!/bin/sh\necho test\n'
        entry=tarfile.TarInfo('bin/ollama');entry.mode=0o755;entry.size=len(data)
        tar.addfile(entry,io.BytesIO(data))
        sym=tarfile.TarInfo('lib/current');sym.type=tarfile.SYMTYPE;sym.linkname=link
        tar.addfile(sym)
    return buf.getvalue()


class ModelManagerTests(unittest.TestCase):
    def test_models_found_from_ollama_manifest_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'models'
            for tag in ('qwen3/4b','gemma3/1b'):
                item=root/'manifests'/'registry.ollama.ai'/'library'/tag
                item.parent.mkdir(parents=True,exist_ok=True)
                item.write_text('{}')
            self.assertEqual(m.offline_model_tags(root),['gemma3:1b','qwen3:4b'])
            records=m.known_model_stores([root])
            record=next(row for row in records if row['path']==str(root))
            self.assertEqual(record['models'],['gemma3:1b','qwen3:4b'])
            self.assertTrue(record['ollama_store'])

    def test_existing_service_and_missing_service(self):
        with patch.object(m.Ollama,'models',return_value=['qwen3:4b']):
            self.assertEqual(m.check_ollama_api('http://127.0.0.1:11434')['models'],['qwen3:4b'])
        with patch.object(m.Ollama,'models',side_effect=ConnectionError('refused')):
            with self.assertRaisesRegex(ConnectionError,'SSH tunnel'):
                m.check_ollama_api('http://localhost:11434')
        with self.assertRaises(ValueError):
            m.check_ollama_api('http://0.0.0.0:11434')

    @unittest.skipIf(os.name=='nt','test Linux tar links on Linux')
    def test_official_archive_layout_with_relative_library_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);archive=path/'fake.tar.zst';archive.write_bytes(fake_archive())
            target=path/'out';target.mkdir()
            with patch.dict(sys.modules,{'zstandard':FakeZstd}):
                m.extract_verified_archive(archive,target,archive.name)
            self.assertEqual((target/'lib/current').resolve(),(target/'bin/ollama').resolve())

    @unittest.skipIf(os.name=='nt','test Unix path traversal on Linux')
    def test_link_outside_staging_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);archive=path/'fake.tar.zst'
            archive.write_bytes(fake_archive('../../../../etc/passwd'))
            target=path/'out';target.mkdir()
            with patch.dict(sys.modules,{'zstandard':FakeZstd}):
                with self.assertRaises(ValueError):
                    m.extract_verified_archive(archive,target,archive.name)

    @unittest.skipIf(os.name=='nt','test Linux managed Ollama workflow')
    def test_verified_installer_handles_existing_runtime(self):
        data=fake_archive()
        with tempfile.TemporaryDirectory() as tmp:
            install=Path(tmp)/'runtime'
            with patch.object(m,'app_runtime_dir',return_value=install), \
                 patch.object(m,'release_asset',return_value=('https://github.com/ollama/ollama/releases/download/mock/ollama-linux-amd64.tar.zst',hashlib.sha256(data).hexdigest(),'ollama-linux-amd64.tar.zst')), \
                 patch('urllib.request.urlopen',return_value=io.BytesIO(data)), \
                 patch.dict(sys.modules,{'zstandard':FakeZstd}):
                got=m.install_managed_runtime()
                self.assertTrue(Path(got).is_file())
                with self.assertRaises(FileExistsError):
                    m.install_managed_runtime()


if __name__ == '__main__':
    unittest.main()
