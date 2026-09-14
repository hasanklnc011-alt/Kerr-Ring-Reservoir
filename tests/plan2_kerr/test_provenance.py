import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmarks.narma10_np.candidate_lock import CandidateLockError
from plan2_kerr import provenance as prov
from plan2_kerr import readout_contract as rc


def minimal(record_id="plan2-kerr-P1-0001", phase=1, **kw):
    kw.setdefault("title", "unit test record")
    kw.setdefault("command", "python -m plan2_kerr.something")
    return prov.ExperimentRecord(experiment_id=record_id, phase=phase, **kw)


class IdTest(unittest.TestCase):
    def test_make_and_validate(self):
        self.assertEqual(prov.make_id(1, 7), "plan2-kerr-P1-0007")
        prov.validate_id("plan2-kerr-P6-9999")

    def test_rejects_malformed_ids(self):
        for bad in ("plan2-kerr-P1-7", "plan2-kerr-P7-0001", "P1-0001",
                    "plan2-kerr-P1-00001", "plan2_kerr-P1-0001"):
            with self.assertRaises(prov.ProvenanceError, msg=bad):
                prov.validate_id(bad)

    def test_rejects_out_of_range_phase_and_serial(self):
        with self.assertRaises(prov.ProvenanceError):
            prov.make_id(7, 1)
        with self.assertRaises(prov.ProvenanceError):
            prov.make_id(1, 10000)

    def test_id_must_match_declared_phase(self):
        with self.assertRaises(prov.ProvenanceError):
            minimal("plan2-kerr-P1-0001", phase=2)

    def test_next_id_skips_used_serials(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertEqual(prov.next_id(1, d), "plan2-kerr-P1-0001")
            prov.write_record(minimal("plan2-kerr-P1-0001"), d)
            self.assertEqual(prov.next_id(1, d), "plan2-kerr-P1-0002")
            self.assertEqual(prov.next_id(2, d), "plan2-kerr-P2-0001")


class ParameterTest(unittest.TestCase):
    def test_status_must_be_known(self):
        with self.assertRaises(prov.ProvenanceError):
            prov.Parameter("n2", 2.4e-19, "m^2/W", "probably-fine", "nowhere")

    def test_every_contract_status_is_accepted(self):
        for status in prov.VALID_STATUSES:
            prov.Parameter("x", 1.0, "m", status, "src")

    def test_unresolved_inputs_are_listed(self):
        record = minimal(parameters=[
            prov.Parameter("n2", 2.4e-19, "m^2/W", "unresolved", "P1 open"),
            prov.Parameter("lambda0", 1.55e-6, "m", "source-supported", "design"),
        ])
        self.assertEqual(record.unresolved_inputs(), ["n2"])
        self.assertIn("UNRESOLVED", record.format_text())


class GateTest(unittest.TestCase):
    def test_no_gates_means_not_passed(self):
        self.assertFalse(minimal().passed)

    def test_all_gates_must_pass(self):
        good = minimal(gates=[prov.GateResult("a", 1.0, 0.5, True)])
        self.assertTrue(good.passed)
        mixed = minimal(gates=[prov.GateResult("a", 1.0, 0.5, True),
                               prov.GateResult("b", 1.0, 2.0, False)])
        self.assertFalse(mixed.passed)


class WriteTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_then_load_roundtrip(self):
        record = minimal(parameters=[
            prov.Parameter("n2", 2.4e-19, "m^2/W", "unresolved", "P1 open")],
            gates=[prov.GateResult("mesh", 1e-3, 5e-4, True, "26 -> 32")])
        path = prov.write_record(record, self.dir)
        again = prov.load_record(path)
        self.assertEqual(again.to_dict(), record.to_dict())

    def test_append_only(self):
        prov.write_record(minimal(), self.dir)
        with self.assertRaises(prov.ProvenanceError) as ctx:
            prov.write_record(minimal(), self.dir)
        self.assertIn("append-only", str(ctx.exception))

    def test_unknown_schema_rejected(self):
        path = self.dir / "plan2-kerr-P1-0001.json"
        path.write_text(json.dumps({"schema": "plan2-kerr-experiment/0"}),
                        encoding="utf-8")
        with self.assertRaises(prov.ProvenanceError):
            prov.load_record(path)

    def test_record_is_deterministic_json(self):
        record = minimal()
        a = json.dumps(record.to_dict(), sort_keys=True)
        b = json.dumps(prov.ExperimentRecord.from_dict(
            json.loads(a)).to_dict(), sort_keys=True)
        self.assertEqual(a, b)


class ArtifactTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.data = self.dir / "result.json"
        self.data.write_text('{"x": 1}', encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_artifact_hashes_the_file(self):
        art = prov.artifact(self.data, "output", repo_root=self.dir)
        self.assertEqual(art.path, "result.json")
        self.assertEqual(art.sha256, prov.sha256_file(self.data))

    def test_missing_artifact_raises(self):
        with self.assertRaises(prov.ProvenanceError):
            prov.artifact(self.dir / "nope.json", "output", repo_root=self.dir)

    def test_verify_detects_a_changed_output(self):
        record = minimal(artifacts=[prov.artifact(self.data, "output",
                                                  repo_root=self.dir)])
        self.assertEqual(prov.verify_record(record, repo_root=self.dir), [])
        self.data.write_text('{"x": 2}', encoding="utf-8")
        problems = prov.verify_record(record, repo_root=self.dir)
        self.assertEqual(len(problems), 1)
        self.assertIn("changed", problems[0])

    def test_verify_detects_a_deleted_output(self):
        record = minimal(artifacts=[prov.artifact(self.data, "output",
                                                  repo_root=self.dir)])
        self.data.unlink()
        self.assertIn("missing", prov.verify_record(record, repo_root=self.dir)[0])

    def test_supersession_skips_the_old_record(self):
        """Append-only: a stale record is superseded, never edited."""
        records = self.dir / "records"
        old = minimal("plan2-kerr-P0-0001", phase=0,
                      artifacts=[prov.artifact(self.data, "output",
                                               repo_root=self.dir)])
        prov.write_record(old, records)
        self.data.write_text('{"x": 99}', encoding="utf-8")

        stale = prov.verify_directory(records, repo_root=self.dir)
        self.assertTrue(stale["plan2-kerr-P0-0001"])  # now failing

        new = minimal("plan2-kerr-P0-0002", phase=0,
                      supersedes="plan2-kerr-P0-0001",
                      artifacts=[prov.artifact(self.data, "output",
                                               repo_root=self.dir)])
        prov.write_record(new, records)

        results = prov.verify_directory(records, repo_root=self.dir)
        self.assertIsNone(results["plan2-kerr-P0-0001"])   # skipped
        self.assertEqual(results["plan2-kerr-P0-0002"], [])

    def test_a_record_cannot_supersede_itself(self):
        with self.assertRaises(prov.ProvenanceError):
            minimal("plan2-kerr-P1-0001", supersedes="plan2-kerr-P1-0001")

    def test_supersedes_must_be_a_valid_id(self):
        with self.assertRaises(prov.ProvenanceError):
            minimal("plan2-kerr-P1-0002", supersedes="nonsense")

    def test_supersedes_survives_the_roundtrip(self):
        record = minimal("plan2-kerr-P1-0002", supersedes="plan2-kerr-P1-0001")
        path = prov.write_record(record, self.dir / "records")
        self.assertEqual(prov.load_record(path).supersedes, "plan2-kerr-P1-0001")

    def test_verify_directory_walks_every_record(self):
        record = minimal(artifacts=[prov.artifact(self.data, "output",
                                                  repo_root=self.dir)])
        prov.write_record(record, self.dir / "records")
        results = prov.verify_directory(self.dir / "records", repo_root=self.dir)
        self.assertEqual(results, {"plan2-kerr-P1-0001": []})


class EnvironmentTest(unittest.TestCase):
    def test_tool_versions_are_real(self):
        tools = prov.tool_versions()
        import numpy
        self.assertEqual(tools["numpy"], numpy.__version__)
        self.assertEqual(tools["python"], __import__("sys").version.split()[0])

    def test_missing_module_is_reported_not_invented(self):
        tools = prov.tool_versions(extra_modules=("definitely_not_installed_xyz",))
        self.assertEqual(tools["definitely_not_installed_xyz"], "not installed")

    def test_git_state_has_the_expected_shape(self):
        state = prov.git_state()
        self.assertIn("commit", state)
        self.assertIn("dirty", state)


class ReadoutContractTest(unittest.TestCase):
    def test_locked_numbers(self):
        self.assertEqual((rc.N_SLOTS, rc.N_PORTS, rc.N_FEATURES), (8, 4, 32))
        self.assertEqual(rc.DIGITAL_TAPS, 0)

    def test_contract_validates_against_the_candidate_lock(self):
        rc.contract().validate()

    def test_contract_rejects_a_mismatched_feature_count(self):
        bad = rc.ReadoutContract(slots=8, ports=4, n_features=40,
                                 sampling=rc.SAMPLING, digital_taps=0,
                                 ridge_selection=rc.RIDGE_SELECTION)
        with self.assertRaises(CandidateLockError):
            bad.validate()

    def test_physics_numbers_are_derived_from_the_model(self):
        from plan2_kerr.memory_triangle import TriangleRequest
        from plan2_kerr.slot_decision import configuration
        ref = configuration(rc.N_SLOTS, rc.N_PORTS,
                            TriangleRequest(retention=rc.RETENTION))
        self.assertAlmostEqual(rc.Q_FLOOR, ref.q_floor)
        self.assertAlmostEqual(rc.MAX_LOSS_DB_PER_CM, ref.max_loss_db_per_cm)

    def test_strict_numbers_are_derived_too(self):
        from plan2_kerr.memory_triangle import TriangleRequest
        from plan2_kerr.slot_decision import configuration
        from plan2_kerr.noise_floor import STRICT_RETENTION
        ref = configuration(rc.N_SLOTS, rc.N_PORTS,
                            TriangleRequest(retention=STRICT_RETENTION))
        self.assertAlmostEqual(rc.Q_FLOOR_STRICT, ref.q_floor)

    def test_beats_the_nominal_plan2_requirement(self):
        from plan2_kerr.memory_triangle import TriangleRequest
        nominal = TriangleRequest().q_floor      # 20 slots, 1/e retention
        self.assertLess(rc.Q_FLOOR, nominal / 2)

    def test_meets_the_realistic_physics_feature_target(self):
        from plan2_kerr.slot_decision import FEATURES_REALISTIC_PHYSICS
        self.assertGreaterEqual(rc.N_FEATURES, FEATURES_REALISTIC_PHYSICS)

    def test_summary_is_serializable_and_cites_the_decision(self):
        summary = rc.summary()
        json.dumps(summary)
        self.assertIn("slot-count", summary["decision"])


if __name__ == "__main__":
    unittest.main()
