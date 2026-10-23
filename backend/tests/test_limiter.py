import pytest
from fastapi.routing import APIRoute
from limits import parse_many

from src.core.limiter import limiter
from src.main import app


# The routes of every router of the app: app.routes only has one entry per router
def api_routes() -> list[APIRoute]:
    included = [route for route in app.routes if hasattr(route, "original_router")]
    routers = [route.original_router for route in included]  # pyright: ignore[reportAttributeAccessIssue]
    return [route for router in routers for route in router.routes if isinstance(route, APIRoute)]


# A day can't be waited for in a test: the limits of each route are read from its decorator
@pytest.mark.parametrize("route, limits", [
    ("demo_router.create_email_request", "5/minute;50/day"),
    ("demo_router.get_email_requests", "60/minute;2000/day"),
])
def test_each_route_has_its_limits(route, limits):
    found = [str(limit.limit) for limit in limiter._route_limits[f"src.api.routers.{route}"]]

    assert found == [str(item) for item in parse_many(limits)]


def test_no_route_goes_without_a_limit():
    routes = [route.endpoint for route in api_routes()]

    assert routes and [
        route.__name__ for route in routes if f"{route.__module__}.{route.__name__}" not in limiter._route_limits
    ] == []
