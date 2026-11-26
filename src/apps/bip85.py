import lvgl as lv
from binascii import hexlify
from io import BytesIO

from app import BaseApp, AppError
from embit import bip85
from bip85_passwords import derive_password, PASSWORD_FORMATS, MAX_INDEX
from gui.common import add_button, add_button_pair, align_button_pair
from gui.decorators import on_release
from gui.screens import Menu, NumericScreen, QRAlert, Alert, Prompt
from gui.screens.mnemonic import MnemonicScreen
import platform

class QRWithSD(QRAlert):
    SAVE = 1
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add save button
        btn = add_button("Save to SD card", on_release(self.save), scr=self)
        btn.align(self.close_button, lv.ALIGN.OUT_TOP_MID, 0, -20)

    def save(self):
        self.set_value(self.SAVE)

class Bip85MnemonicScreen(MnemonicScreen):
    QR = 1
    SD = 2
    LOAD = 3
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_btn = add_button(
            text="Use now (load to device)",
            scr=self,
            callback=on_release(self.load)
        )
        self.load_btn.align(self.table, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
        self.show_qr_btn, self.save_sd_btn = add_button_pair(
            text1="Show QR code",
            callback1=on_release(self.show_qr),
            text2="Save to SD card",
            callback2=on_release(self.save_sd),
            scr=self,
        )
        self.show_qr_btn.align(self.load_btn, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
        self.save_sd_btn.align(self.load_btn, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
        align_button_pair(self.show_qr_btn, self.save_sd_btn)

    def show_qr(self):
        self.set_value(self.QR)

    def save_sd(self):
        self.set_value(self.SD)

    def load(self):
        self.set_value(self.LOAD)

class PasswordNumericScreen(NumericScreen):
    """Numeric entry with an explicit way to cancel."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_button("Back", on_release(self.cancel), scr=self, y=300)

    def cancel(self):
        self.ta.set_text("")
        self.set_value(None)


class App(BaseApp):
    """
    WalletManager class manages your wallets.
    It stores public information about the wallets
    in the folder and signs it with keystore's id key
    """

    button = "Deterministic derivation (BIP-85)"
    name = "bip85"

    async def menu(self, show_screen):
        buttons = [
            (None, "Mnemonics"),
            (0, "12-word mnemonic"),
            (1, "18-word mnemonic"),
            (2, "24-word mnemonic"),
            (None, "Other stuff"),
            (3, "WIF key (single private key)"),
            (4, "Master private key (xprv)"),
            (5, "Raw entropy (16-64 bytes)"),
            (None, "Passwords"),
            (6, "Base64 password"),
            (7, "Base85 password"),
        ]

        # wait for menu selection
        menuitem = await show_screen(
            Menu(
                buttons,
                last=(255, None),
                title="What do you want to derive?",
                note="",
            )
        )

        # process the menu button:
        # back button
        if menuitem == 255:
            return False
        if menuitem in (6, 7):
            return await self.password_menu(show_screen, 64 if menuitem == 6 else 85)
        # get derivation index
        index = await show_screen(
            NumericScreen(title="Enter derivation index", note="Default: 0")
        )
        if index is None:
            return True # stay in the menu
        if index == "":
            index = 0
        index = int(index)
        note = "index: %d" % index

        fgp = hexlify(self.keystore.fingerprint).decode()
        # mnemonic menu items
        if menuitem >= 0 and menuitem <=2:
            num_words = 12+6*menuitem
            mnemonic = bip85.derive_mnemonic(
                self.keystore.root, num_words=num_words, index=index
            )
            title = "Derived %d-word mnemonic" % num_words
            action = await show_screen(
                Bip85MnemonicScreen(mnemonic=mnemonic, title=title, note=note)
            )
            if action == Bip85MnemonicScreen.QR:
                await show_screen(
                    QRAlert(title=title, message=mnemonic, note=note)
                )
            elif action == Bip85MnemonicScreen.SD:
                fname = "bip85-%s-mnemonic-%d-%d.txt" % (
                    fgp, num_words, index
                )
                with platform.sdcard as sd:
                    if sd.file_exists(fname):
                        scr = Prompt("Overwrite?", message="File %s already exists on the SD card. Overwrite?" % fname)
                        confirm = await show_screen(scr)
                        if not confirm:
                            return True
                    with sd.open(fname, "w") as f:
                        f.write(mnemonic)
                await show_screen(
                    Alert(
                        title="Success",
                        message="Mnemonic is saved as\n\n%s" % fname,
                        button_text="Close",
                    )
                )
            elif action == Bip85MnemonicScreen.LOAD:
                await self.communicate(
                    BytesIO(b"set_mnemonic "+mnemonic.encode()), app="",
                )
                return False
            return True
        # other stuff
        if menuitem == 3:
            title = "Derived private key"
            res = bip85.derive_wif(self.keystore.root, index)
            file_suffix = "wif"
        elif menuitem == 4:
            title = "Derived master private key"
            res = bip85.derive_xprv(self.keystore.root, index)
            file_suffix = "xprv"
        elif menuitem == 5:
            num_bytes = await show_screen(
                NumericScreen(
                    title="Number of bytes to generate",
                    note="16 <= N <= 64. Default: 32",
                )
            )
            if num_bytes is None:
                return True
            if num_bytes == "":
                num_bytes = 32
            num_bytes = int(num_bytes)
            if num_bytes < 16 or num_bytes > 64:
                raise AppError("Only 16-64 bytes can be generated with BIP-85")
            title = "Derived %d-byte entropy" % num_bytes
            raw = bip85.derive_hex(self.keystore.root, num_bytes, index)
            res = hexlify(raw).decode()
            file_suffix = "hex-%d" % num_bytes
        else:
            raise NotImplementedError("Not implemented")
        res = str(res)
        action = await show_screen(
            QRWithSD(title=title, message=res, note=note)
        )
        if action == QRWithSD.SAVE:
            fname = "bip85-%s-%s-%d.txt" % (fgp, file_suffix, index)
            with platform.sdcard as sd:
                with sd.open(fname, "w") as f:
                    f.write(res)
            await show_screen(
                Alert(
                    title="Success",
                    message="Data is saved as\n\n%s" % fname,
                    button_text="Close",
                )
            )
        return True

    async def password_menu(self, show_screen, base):
        app, minimum, maximum = PASSWORD_FORMATS[base]
        title = "Base%d password" % base
        length = await show_screen(
            PasswordNumericScreen(
                title="Enter password length",
                note="%d-%d characters. Default: 24" % (minimum, maximum),
            )
        )
        if length is None:
            return True
        if len(length) > 2:
            raise AppError("Invalid password length")
        length = int(length or "24")
        if not minimum <= length <= maximum:
            raise AppError("Password length must be %d-%d" % (minimum, maximum))
        index = await show_screen(
            PasswordNumericScreen(
                title="Enter derivation index",
                note="0-%d. Default: 0" % MAX_INDEX,
            )
        )
        if index is None:
            return True
        if len(index) > 10:
            raise AppError("Invalid derivation index")
        index = int(index or "0")
        if not 0 <= index <= MAX_INDEX:
            raise AppError("Invalid derivation index")
        path = "m/83696968'/%d'/%d'/%d'" % (app, length, index)
        reveal = await show_screen(
            Prompt(
                title=title,
                message=path + "\n\nKeep the format, length and index for recovery. "
                "Anyone with your root seed can derive this password. "
                "Use a separate seed for password management.",
                confirm_text="Reveal",
            )
        )
        if not reveal:
            return True
        password = derive_password(self.keystore.root, base, length, index)
        # Never use QRWithSD: passwords must not be written to disk or logged.
        show_qr = await show_screen(
            Prompt(
                title=title,
                message=path + "\n\n" + password + "\n\n"
                "Anyone who scans the QR can read this password.",
                confirm_text="Show QR",
                cancel_text="Close",
            )
        )
        if show_qr:
            await show_screen(
                QRAlert(
                    title=title,
                    message=path,
                    qr_message=password,
                    sensitive=True,
                )
            )
        return True
