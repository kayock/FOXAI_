from __future__ import annotations

from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from core.model_sources import ModelSourceError, ModelSourceRegistry


class ModelSourceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.usb = self.base / 'FOXAI'
        self.host = self.base / 'HostModels'
        (self.usb / 'Models' / 'Chat').mkdir(parents=True)
        self.host.mkdir(parents=True)
        self.usb_model = self.usb / 'Models' / 'Chat' / 'usb-model.gguf'
        self.host_model = self.host / 'host-model.gguf'
        self.usb_model.write_bytes(b'usb-model')
        self.host_model.write_bytes(b'host-model')
        self.config = self.usb / 'Config' / 'model_sources.json'
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({
            'schema': 'foxai.model-sources.v1',
            'policy': {
                'no_whole_drive_scan': True,
                'never_modify_model_files': True,
                'no_silent_model_switch': True,
                'automatic_model_launch': False,
                'online_sources_enabled': False,
                'credentials_in_plain_config': False,
            },
            'usb_roots': [
                {'id': 'usb_chat', 'path': 'Models/Chat', 'enabled': True},
            ],
            'machines': {},
            'reserved_source_types': {
                'LAN_OPENAI_COMPATIBLE': {'enabled': False},
                'ONLINE_PROVIDER': {'enabled': False},
            },
        }, indent=2), encoding='utf-8')
        self.registry = ModelSourceRegistry(
            self.usb,
            config_path=self.config,
            machine_name='TEST-PC',
        )
        self.host_hash = hashlib.sha256(self.host_model.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def test_usb_catalog_is_available_without_machine_profile(self):
        catalog = self.registry.catalog(force=True)
        self.assertEqual(1, len(catalog))
        self.assertEqual('USB', catalog[0]['source'])
        self.assertFalse(self.registry.state()['machine']['configured'])

    def test_session_folder_is_not_persisted(self):
        before = self.config.read_bytes()
        result = self.registry.approve_folder(
            self.host,
            remember=False,
            confirm=True,
        )
        self.assertTrue(result['ok'])
        self.assertEqual('session', result['scope'])
        self.assertEqual(before, self.config.read_bytes())
        self.assertEqual(1, self.registry.state()['counts']['host_pc'])

    def test_remembered_folder_builds_machine_registry(self):
        result = self.registry.approve_folder(
            self.host,
            remember=True,
            confirm=True,
        )
        self.assertTrue(result['ok'])
        data = json.loads(self.config.read_text(encoding='utf-8'))
        profile = data['machines']['TEST-PC']
        self.assertEqual('ASK_OR_APPROVED_USB', profile['fallback_policy'])
        self.assertFalse(profile['allow_online_sources'])
        self.assertEqual(str(self.host.resolve()), profile['approved_host_roots'][0]['path'])

    def test_approval_requires_explicit_confirmation(self):
        with self.assertRaises(ModelSourceError):
            self.registry.approve_folder(
                self.host,
                remember=True,
                confirm=False,
            )

    def test_whole_drive_or_filesystem_root_is_rejected(self):
        with self.assertRaises(ModelSourceError):
            self.registry.approve_folder(
                Path(self.base.anchor),
                remember=False,
                confirm=True,
            )

    def test_forget_folder_removes_reference_not_model(self):
        self.registry.approve_folder(self.host, remember=True, confirm=True)
        result = self.registry.forget_folder(self.host, confirm=True)
        self.assertTrue(result['ok'])
        self.assertTrue(self.host_model.is_file())
        self.assertEqual(
            self.host_hash,
            hashlib.sha256(self.host_model.read_bytes()).hexdigest(),
        )
        self.assertEqual(0, self.registry.state()['counts']['host_pc'])

    def test_forget_model_only_removes_preference(self):
        self.registry.approve_folder(self.host, remember=True, confirm=True)
        data = json.loads(self.config.read_text(encoding='utf-8'))
        data['machines']['TEST-PC']['preferred_models'] = {
            'general': str(self.host_model.resolve())
        }
        self.config.write_text(json.dumps(data, indent=2), encoding='utf-8')
        result = self.registry.forget_model(self.host_model, confirm=True)
        self.assertTrue(result['ok'])
        self.assertTrue(self.host_model.is_file())
        self.assertEqual(
            self.host_hash,
            hashlib.sha256(self.host_model.read_bytes()).hexdigest(),
        )

    def test_forget_machine_keeps_usb_and_host_files(self):
        self.registry.approve_folder(self.host, remember=True, confirm=True)
        result = self.registry.forget_machine(confirm=True)
        self.assertTrue(result['ok'])
        self.assertTrue(self.usb_model.is_file())
        self.assertTrue(self.host_model.is_file())
        state = self.registry.state()
        self.assertFalse(state['machine']['configured'])
        self.assertEqual(1, state['counts']['usb'])
        self.assertEqual(0, state['counts']['host_pc'])

    def test_online_and_lan_sources_remain_disabled(self):
        state = self.registry.state()
        self.assertFalse(state['allow_online_sources'])
        self.assertFalse(state['reserved_source_types']['ONLINE_PROVIDER']['enabled'])
        self.assertFalse(state['reserved_source_types']['LAN_OPENAI_COMPATIBLE']['enabled'])

    def test_no_silent_fallback_contract_is_present(self):
        state = self.registry.state()
        self.assertTrue(state['policy']['no_silent_model_switch'])
        self.assertEqual('ASK_OR_APPROVED_USB', state['fallback_policy'])


if __name__ == '__main__':
    unittest.main()
