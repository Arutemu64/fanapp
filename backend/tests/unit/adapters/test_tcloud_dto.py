import pytest

from fanfan.adapters.api.ticketscloud.dto.order import OrdersResponse, OrderStatus
from fanfan.adapters.api.ticketscloud.dto.refund import RefundsResponse
from fanfan.adapters.serialization import create_retort

pytestmark = pytest.mark.unit

ORDERS_PAYLOAD = {
    "data": [
        {
            "code": "97elgi8j",
            "created_at": "2019-07-25 14:56:16",
            "event": "5d31fbdd27649b0dff076117",
            "id": "5d39c3108cd381a4891e07e0",
            "settings": {"invitation": False, "send_tickets": False},
            "status": "done",
            "tickets": [
                {
                    "barcode": "17174251182011730",
                    "discount": "0.00",
                    "extra": "6.00",
                    "full": "156.00",
                    "id": "5d31fbfb306fdcc187b91179",
                    "nominal": "150.00",
                    "number": 157495,
                    "price": "150.00",
                    "serial": "OOX",
                    "set": "5d31fbfa27649b0dff07611b",
                    "status": "reserved",
                }
            ],
            "values": {"full": "156.00"},
            "vendor_data": {},
        }
    ],
    "pagination": {"page": 1, "page_size": 50, "total": 1},
    "refs": {"events": {}, "partners": {}},
}

REFUNDS_PAYLOAD = {
    "data": [
        {
            "created_at": "2018-07-24 13:26:00",
            "culprit": "user",
            "event": "5b23b53b9c9b19000c6c4180",
            "id": "5b5728e886e7040069eb7f86",
            "order": "5b57281886e704000b424741",
            "policy": "general",
            "refund_nominal": "13500.00",
            "status": "approved",
            "tickets": ["5dd5469b05fe4df8940eb613"],
        }
    ],
    "pagination": {"page": 1, "page_size": 50, "total": 1},
    "refs": {"events": {}, "orders": {}},
}


def test_orders_response_loads_documented_payload() -> None:
    response = create_retort().load(ORDERS_PAYLOAD, OrdersResponse)

    order = response.data[0]
    assert order.id == "5d39c3108cd381a4891e07e0"
    assert order.status is OrderStatus.DONE
    assert order.tickets[0].barcode == "17174251182011730"
    assert response.pagination.total == 1


def test_refunds_response_loads_documented_payload() -> None:
    response = create_retort().load(REFUNDS_PAYLOAD, RefundsResponse)

    refund = response.data[0]
    assert refund.order == "5b57281886e704000b424741"
    assert refund.tickets == ["5dd5469b05fe4df8940eb613"]
