import asyncio
import gc
import sys

if sys.implementation.name != "micropython":
    from native_support import setup_native_stubs

    setup_native_stubs()

from unittest import TestCase

from tests.util import clear_testdir, get_keystore, get_wallets_app


HIGH_FEE = "Fee is 10.00% of the send amount - unusually high!"
LIQUID_UNASSESSABLE = (
    "Fee cannot be assessed automatically for this multi-asset transaction. "
    "Please verify the fee manually!"
)


class WalletManagerWarningsTest(TestCase):
    def setUp(self):
        clear_testdir()
        self.manager = get_wallets_app(get_keystore(), "regtest").manager

    def tearDown(self):
        clear_testdir()
        gc.collect()

    def warnings_for(self, fee, outputs, inputs=None, wallets=None, warnings=None):
        meta = {"fee": fee, "outputs": outputs, "inputs": inputs or []}
        if warnings is not None:
            meta["warnings"] = warnings
        self.manager.add_warnings(meta, wallets)
        return meta

    def test_fee_below_threshold_does_not_warn(self):
        meta = self.warnings_for(999, [{"value": 10_000, "change": False}])
        self.assertEqual(meta.get("warnings", []), [])
        self.assertNotIn("fee_warning", meta)

    def test_fee_exactly_at_threshold_warns(self):
        meta = self.warnings_for(1_000, [{"value": 10_000, "change": False}])
        self.assertEqual(meta["warnings"], [HIGH_FEE])
        self.assertEqual(meta["fee_warning"], HIGH_FEE)

    def test_fee_above_threshold_warns(self):
        meta = self.warnings_for(1_001, [{"value": 10_000, "change": False}])
        self.assertEqual(
            meta["warnings"],
            ["Fee is 10.01% of the send amount - unusually high!"],
        )

    def test_owned_outputs_are_excluded_from_fee_basis(self):
        meta = self.warnings_for(
            100,
            [
                {"value": 1_000, "owned": False, "change": False},
                {"value": 50_000, "owned": True, "change": False},
            ],
            inputs=[{"value": 51_100}],
        )
        self.assertEqual(meta["fee_basis"], 1_000)
        self.assertEqual(meta["warnings"], [HIGH_FEE])

    def test_self_transfer_falls_back_to_verified_total_inputs(self):
        meta = self.warnings_for(
            2_000,
            [{"value": 18_000, "change": True, "owned": True}],
            inputs=[{"value": 12_000}, {"value": 8_000}],
        )
        self.assertEqual(meta["fee_basis"], 20_000)
        self.assertFalse(meta["fee_basis_is_send_amount"])
        self.assertEqual(
            meta["warnings"],
            ["Fee is 10.00% of total inputs (self-transfer) - unusually high!"],
        )

    def test_fee_percent_is_precomputed(self):
        meta = self.warnings_for(1_000, [{"value": 10_000, "change": False}])
        self.assertEqual(meta["fee_percent"], 10.0)

        nofee = {"outputs": [{"value": 10_000, "change": False}], "inputs": []}
        self.manager.add_warnings(nofee)
        self.assertIsNone(nofee["fee_percent"])

    def test_existing_warnings_are_preserved_and_not_duplicated(self):
        wallet_a = object()
        wallet_b = object()
        wallets = {wallet_a: {}, wallet_b: {}}
        meta = self.warnings_for(
            1_000,
            [{"value": 10_000, "change": False}],
            wallets=wallets,
            warnings=["Existing warning!"],
        )
        self.manager.add_warnings(meta, wallets)
        self.assertEqual(
            meta["warnings"],
            [
                "Existing warning!",
                "Mixed inputs from different wallets!",
                HIGH_FEE,
            ],
        )

    def test_liquid_same_asset_uses_percentage_warning(self):
        liquid = get_wallets_app(get_keystore(), "elementsregtest").manager
        asset = b"a" * 32
        meta = {
            "fee": 1_000,
            "fee_asset": asset,
            "outputs": [
                {"value": 10_000, "asset_id": asset, "owned": False},
                {"value": 1_000, "asset_id": asset, "fee_output": True},
            ],
            "inputs": [{"value": 11_000, "asset_id": asset}],
        }
        liquid.add_warnings(meta)
        self.assertEqual(meta["fee_warning"], HIGH_FEE)
        self.assertEqual(meta["fee_percent"], 10.0)

    def test_liquid_different_asset_uses_manual_review_warning(self):
        liquid = get_wallets_app(get_keystore(), "elementsregtest").manager
        fee_asset = b"a" * 32
        sent_asset = b"b" * 32
        meta = {
            "fee": 1_000,
            "fee_asset": fee_asset,
            "outputs": [
                {"value": 10_000, "asset_id": sent_asset, "owned": False},
                {"value": 1_000, "asset_id": fee_asset, "fee_output": True},
            ],
            "inputs": [
                {"value": 10_000, "asset_id": sent_asset},
                {"value": 1_000, "asset_id": fee_asset},
            ],
        }
        liquid.add_warnings(meta)
        self.assertEqual(meta["fee_warning"], LIQUID_UNASSESSABLE)
        self.assertIsNone(meta["fee_percent"])

    @staticmethod
    def _run(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_fee_warning_must_be_acknowledged_before_final_confirmation(self):
        reached = []

        async def show_screen(scr):
            return True

        async def fake_fee_warning(meta, show):
            return False

        async def fake_final(wallets, meta, show):
            reached.append(True)
            return True

        self.manager.confirm_fee_warning = fake_fee_warning
        self.manager.confirm_transaction_final = fake_final
        result = self._run(
            self.manager.confirm_transaction(
                {object(): {"amount": 0}},
                {"inputs": [{}], "outputs": [], "signed_inputs": 0},
                show_screen,
            )
        )
        self.assertIsNone(result)
        self.assertEqual(reached, [])

    def test_fee_warning_acknowledgement_allows_final_confirmation(self):
        reached = []

        async def show_screen(scr):
            return True

        async def fake_fee_warning(meta, show):
            return True

        async def fake_final(wallets, meta, show):
            reached.append(True)
            return True

        self.manager.confirm_fee_warning = fake_fee_warning
        self.manager.confirm_transaction_final = fake_final
        result = self._run(
            self.manager.confirm_transaction(
                {object(): {"amount": 0}},
                {"inputs": [{}], "outputs": [], "signed_inputs": 0},
                show_screen,
            )
        )
        self.assertEqual(result, {"sighash": None})
        self.assertEqual(reached, [True])
