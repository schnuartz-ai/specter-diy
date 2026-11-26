"""BIP85 password applications (BIP85, PWD BASE64 and PWD BASE85)."""
from binascii import b2a_base64
from embit import bip85

MAX_INDEX = 0x7fffffff
PASSWORD_FORMATS = {
    64: (707764, 20, 86),
    85: (707785, 10, 80),
}
# RFC 1924 alphabet, as required by the BIP85 PWD BASE85 test vector.
BASE85_ALPHABET = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~"


def _encode_base85(entropy):
    # BIP85 always provides 64 bytes, so no partial groups or padding.
    result = bytearray(80)
    for offset in range(0, 64, 4):
        value = 0
        for i in range(4):
            value = (value << 8) | entropy[offset + i]
        pos = offset // 4 * 5
        for i in range(4, -1, -1):
            value, digit = divmod(value, 85)
            result[pos + i] = BASE85_ALPHABET[digit]
    return bytes(result)


def derive_password(root, base, length, index=0):
    """Derive a standard BIP85 password from a BIP32 root key."""
    if type(base) is not int or base not in PASSWORD_FORMATS:
        raise ValueError("Unsupported password format")
    app, minimum, maximum = PASSWORD_FORMATS[base]
    if type(length) is not int or not minimum <= length <= maximum:
        raise ValueError("Invalid password length")
    if type(index) is not int or not 0 <= index <= MAX_INDEX:
        raise ValueError("Invalid derivation index")
    entropy = bip85.derive_entropy(root, app, [length, index])
    if len(entropy) != 64:
        raise ValueError("Invalid BIP85 entropy length")
    if base == 64:
        encoded = b2a_base64(entropy).strip()
    else:
        encoded = _encode_base85(entropy)
    # Length limits ensure that no Base64 padding is returned.
    return encoded[:length].decode()
