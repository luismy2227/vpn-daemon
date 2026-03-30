from __future__ import annotations

import pytest
import pyotp

from vpn_daemon.otp import build_otp_password

_SECRET = "JBSWY3DPEHPK3PXP"  # well-known test secret


def test_build_otp_password_format():
    result = build_otp_password("pin", _SECRET)
    # pin (3) + 6-digit TOTP code
    assert result.startswith("pin")
    assert len(result) == 3 + 6
    assert result[3:].isdigit()


def test_build_otp_password_empty_pin():
    result = build_otp_password("", _SECRET)
    assert len(result) == 6
    assert result.isdigit()


def test_build_otp_password_matches_pyotp():
    code = pyotp.TOTP(_SECRET).now()
    assert build_otp_password("", _SECRET) == code
    assert build_otp_password("abc", _SECRET) == "abc" + code


def test_build_otp_password_invalid_secret():
    with pytest.raises(Exception):
        build_otp_password("pin", "NOT_VALID_BASE32!!!")
