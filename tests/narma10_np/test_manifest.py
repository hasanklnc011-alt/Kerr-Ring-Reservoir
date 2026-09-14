import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.narma10_np import config
from benchmarks.narma10_np import manifest as m


SMALL = config.SeedSpec(
    namespace="narma10/test", master_seed=1234, count=3,
    washout=10, train_len=40, test_len=20,
)


class ManifestRoundTripTest(unittest.TestCase):
    def test_build_then_verify_ok(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "m.json"
            m.write_manifest(SMALL, path)
            result = m.verify_manifest(path)
            self.assertTrue(result.ok, result.mismatches)
            result.raise_for_status()

    def test_deterministic_digest(self):
        self.assertEqual(
            m.build_manifest(SMALL)["manifest_digest"],
            m.build_manifest(SMALL)["manifest_digest"],
        )

    def test_entry_count_matches_spec(self):
        self.assertEqual(len(m.build_manifest(SMALL)["entries"]), SMALL.count)


class ManifestTamperTest(unittest.TestCase):
    def _write(self, d: str) -> Path:
        path = Path(d) / "m.json"
        m.write_manifest(SMALL, path)
        return path

    def test_flipped_data_hash_detected(self):
        with TemporaryDirectory() as d:
            path = self._write(d)
            data = json.loads(path.read_text())
            data["entries"][1]["target_sha256"] = "0" * 64
            data["manifest_digest"] = m.manifest_digest(data)  # keep body consistent
            path.write_text(json.dumps(data))
            result = m.verify_manifest(path)
            self.assertFalse(result.ok)
            self.assertTrue(any("target_sha256" in x for x in result.mismatches))
            with self.assertRaises(m.ManifestMismatch):
                result.raise_for_status()

    def test_broken_digest_detected(self):
        with TemporaryDirectory() as d:
            path = self._write(d)
            data = json.loads(path.read_text())
            data["manifest_digest"] = "deadbeef"
            path.write_text(json.dumps(data))
            result = m.verify_manifest(path)
            self.assertFalse(result.ok)
            self.assertTrue(any("manifest_digest" in x for x in result.mismatches))

    def test_changed_spec_param_detected(self):
        with TemporaryDirectory() as d:
            path = self._write(d)
            data = json.loads(path.read_text())
            data["spec"]["master_seed"] = 9999
            data["manifest_digest"] = m.manifest_digest(data)
            path.write_text(json.dumps(data))
            result = m.verify_manifest(path)
            self.assertFalse(result.ok)

    def test_schema_mismatch_detected(self):
        with TemporaryDirectory() as d:
            path = self._write(d)
            data = json.loads(path.read_text())
            data["schema"] = "narma10-manifest/999"
            data["manifest_digest"] = m.manifest_digest(data)
            path.write_text(json.dumps(data))
            self.assertFalse(m.verify_manifest(path).ok)

    def test_extra_entry_detected(self):
        with TemporaryDirectory() as d:
            path = self._write(d)
            data = json.loads(path.read_text())
            data["entries"].append(dict(data["entries"][0], index=99))
            data["manifest_digest"] = m.manifest_digest(data)
            path.write_text(json.dumps(data))
            self.assertFalse(m.verify_manifest(path).ok)


class CommittedManifestsTest(unittest.TestCase):
    """The manifests checked into the repo must verify as-is."""

    def test_repo_manifests_verify(self):
        for spec in (config.dev_spec(), config.blind_spec()):
            path = m.default_path(spec)
            self.assertTrue(path.exists(), f"missing committed manifest {path}")
            result = m.verify_manifest(path)
            self.assertTrue(result.ok, result.mismatches)

    def test_blind_spec_has_ten_entries(self):
        path = m.default_path(config.blind_spec())
        data = json.loads(path.read_text())
        self.assertEqual(len(data["entries"]), 10)

    def test_dev_and_blind_digests_differ(self):
        self.assertNotEqual(
            m.load_digest(m.default_path(config.dev_spec())),
            m.load_digest(m.default_path(config.blind_spec())),
        )


if __name__ == "__main__":
    unittest.main()
