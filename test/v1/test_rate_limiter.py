from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.utils.limiter import RateLimiter
def mock_endpoint():
    return {"message": "ok"}

def test_custom_rate_limiter_works():
    """
    Verifies that the SimpleRateLimiter middleware blocks requests
    after the defined limit (2/minute) is exceeded.
    """
    test_app = FastAPI()
    test_app.add_middleware(RateLimiter, limit="2/minute")
    test_app.add_api_route("/", mock_endpoint, methods=["GET"])

    with TestClient(test_app) as client:
        res1 = client.get("/")
        assert res1.status_code == 200

        res2 = client.get("/")
        assert res2.status_code == 200

        res3 = client.get("/")
        assert res3.status_code == 429
        
        json_resp = res3.json()
        assert json_resp["status"] == "error"
        assert "Rate limit exceeded" in json_resp["message"]