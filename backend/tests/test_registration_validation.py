import pytest
from pydantic import ValidationError

from app.schemas.activity import AdminRegistrationCreate, RegistrationCreate


def registration_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "activity_slug": "flipbelt-40s",
        "channel": "h5",
        "external_id": "13800138000",
        "name": "测试选手·A-1",
        "phone": "13800138000",
        "number_plate": "沪A-亲子组-07",
    }
    payload.update(overrides)
    return payload


def test_registration_accepts_free_form_name_and_number_plate() -> None:
    registration = RegistrationCreate(**registration_payload())

    assert registration.name == "测试选手·A-1"
    assert registration.number_plate == "沪A-亲子组-07"


@pytest.mark.parametrize("phone", ["1380013800", "138001380000", "1380013800a"])
def test_registration_requires_exactly_eleven_phone_digits(phone: str) -> None:
    with pytest.raises(ValidationError):
        RegistrationCreate(**registration_payload(phone=phone))


def test_admin_registration_uses_the_same_phone_rule() -> None:
    registration = AdminRegistrationCreate(
        name="选手（补录）",
        phone="13900139000",
        number_plate="少年组/9号",
    )

    assert registration.phone == "13900139000"
    assert registration.number_plate == "少年组/9号"

