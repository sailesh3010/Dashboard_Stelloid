"""
API tests for the Stelloid Command Center Dashboard.

Covers all required acceptance criteria:
1. Overview endpoint — valid response with correct fields
2. Trends endpoint — time-series data structure
3. Channel distribution — metric-based comparison
4. Filtering — channel and business_scope filters
5. Invalid request — proper error responses
6. Channels list endpoint
7. Health check
"""


class TestHealthCheck:
    """Test the /health endpoint."""

    def test_health_returns_healthy(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestChannels:
    """Test the /api/v1/channels endpoint."""

    def test_list_channels(self, client):
        response = client.get("/api/v1/channels")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        names = {ch["name"] for ch in data}
        assert "Shopify" in names
        assert "Amazon US" in names
        assert "Walmart Marketplace" in names

        # Each channel must have id, name, business_scope
        for ch in data:
            assert "id" in ch
            assert "name" in ch
            assert "business_scope" in ch


class TestOverview:
    """Test the /api/v1/overview endpoint."""

    def test_overview_without_filters(self, client):
        response = client.get("/api/v1/overview")
        assert response.status_code == 200

        data = response.json()
        assert "date_range" in data
        assert "overview" in data

        overview = data["overview"]
        assert "gmv" in overview
        assert "net_revenue" in overview
        assert "contribution" in overview
        assert "returns_refunds" in overview
        assert "net_orders" in overview
        assert "average_order_value" in overview

        # All values should be positive
        assert overview["gmv"] > 0
        assert overview["net_revenue"] > 0
        assert overview["net_orders"] > 0
        assert overview["average_order_value"] > 0

    def test_overview_with_date_range(self, client):
        response = client.get(
            "/api/v1/overview",
            params={"start_date": "2026-09-20", "end_date": "2026-09-25"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["date_range"]["start"] == "2026-09-20"
        assert data["date_range"]["end"] == "2026-09-25"

    def test_overview_with_channel_filter(self, client):
        response = client.get(
            "/api/v1/overview",
            params={"channel": "Shopify"},
        )
        assert response.status_code == 200

        data = response.json()
        overview = data["overview"]
        # Shopify-only values should be less than total
        assert overview["gmv"] > 0

    def test_overview_with_business_scope_filter(self, client):
        response = client.get(
            "/api/v1/overview",
            params={"business_scope": "Marketplace"},
        )
        assert response.status_code == 200

        data = response.json()
        overview = data["overview"]
        assert overview["gmv"] > 0

    def test_overview_invalid_date_range(self, client):
        """start_date after end_date should return 400."""
        response = client.get(
            "/api/v1/overview",
            params={"start_date": "2026-10-01", "end_date": "2026-09-01"},
        )
        assert response.status_code == 400
        assert "start_date" in response.json()["detail"]


class TestTrends:
    """Test the /api/v1/trends endpoint."""

    def test_trends_returns_time_series(self, client):
        response = client.get(
            "/api/v1/trends",
            params={"start_date": "2026-09-20", "end_date": "2026-09-29"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "date_range" in data
        assert "trends" in data

        trends = data["trends"]
        assert isinstance(trends, list)
        assert len(trends) == 10  # 10 days of test data

        # Each point must have date, net_revenue, contribution
        for point in trends:
            assert "date" in point
            assert "net_revenue" in point
            assert "contribution" in point
            assert point["net_revenue"] > 0
            assert point["contribution"] > 0

    def test_trends_dates_are_sorted(self, client):
        response = client.get("/api/v1/trends")
        assert response.status_code == 200

        dates = [p["date"] for p in response.json()["trends"]]
        assert dates == sorted(dates)

    def test_trends_with_channel_filter(self, client):
        response = client.get(
            "/api/v1/trends",
            params={"channel": "Amazon US"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["trends"]) > 0


class TestChannelDistribution:
    """Test the /api/v1/channel-distribution endpoint."""

    def test_distribution_default_metric(self, client):
        response = client.get("/api/v1/channel-distribution")
        assert response.status_code == 200

        data = response.json()
        assert data["metric"] == "net_revenue"
        assert "distribution" in data
        assert len(data["distribution"]) == 3

        # Each entry must have channel and value
        for entry in data["distribution"]:
            assert "channel" in entry
            assert "value" in entry
            assert entry["value"] > 0

    def test_distribution_custom_metric(self, client):
        response = client.get(
            "/api/v1/channel-distribution",
            params={"metric": "gmv"},
        )
        assert response.status_code == 200
        assert response.json()["metric"] == "gmv"

    def test_distribution_invalid_metric(self, client):
        """Invalid metric name should return 400."""
        response = client.get(
            "/api/v1/channel-distribution",
            params={"metric": "invalid_metric"},
        )
        assert response.status_code == 400
        assert "Invalid metric" in response.json()["detail"]

    def test_distribution_sorted_descending(self, client):
        response = client.get("/api/v1/channel-distribution")
        assert response.status_code == 200

        values = [e["value"] for e in response.json()["distribution"]]
        assert values == sorted(values, reverse=True)


class TestChannelPerformance:
    """Test the /api/v1/channel-performance endpoint."""

    def test_performance_returns_all_channels(self, client):
        response = client.get("/api/v1/channel-performance")
        assert response.status_code == 200

        data = response.json()
        assert "date_range" in data
        assert "channels" in data
        assert len(data["channels"]) == 3

        # Each channel entry should have all KPI fields
        required_fields = {
            "channel", "gmv", "net_revenue", "contribution",
            "returns_refunds", "net_orders", "average_order_value",
        }
        for ch in data["channels"]:
            assert required_fields.issubset(ch.keys())
            assert ch["net_orders"] > 0
            assert ch["average_order_value"] > 0

    def test_performance_with_channel_filter(self, client):
        response = client.get(
            "/api/v1/channel-performance",
            params={"channel": "Walmart Marketplace"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["channels"]) == 1
        assert data["channels"][0]["channel"] == "Walmart Marketplace"

    def test_performance_aov_consistency(self, client):
        """Average order value should equal GMV / net_orders."""
        response = client.get("/api/v1/channel-performance")
        assert response.status_code == 200

        for ch in response.json()["channels"]:
            expected_aov = round(ch["gmv"] / ch["net_orders"], 2)
            assert ch["average_order_value"] == expected_aov

    def test_performance_pagination(self, client):
        """Pagination limit and offset should control returned channel items."""
        # Query total count
        full_res = client.get("/api/v1/channel-performance")
        assert full_res.status_code == 200
        assert full_res.json()["total_count"] == 3

        # Query with limit=1, offset=1
        paged_res = client.get("/api/v1/channel-performance", params={"limit": 1, "offset": 1})
        assert paged_res.status_code == 200
        paged_data = paged_res.json()
        assert paged_data["total_count"] == 3
        assert len(paged_data["channels"]) == 1
        assert paged_data["channels"][0]["channel"] == full_res.json()["channels"][1]["channel"]

    def test_api_cache_headers(self, client):
        """API GET endpoints should return Cache-Control headers."""
        response = client.get("/api/v1/overview")
        assert response.status_code == 200
        assert "cache-control" in response.headers
        assert "max-age=60" in response.headers["cache-control"]


class TestInvalidRequests:
    """Test error handling for various invalid requests."""

    def test_invalid_date_format(self, client):
        """Non-date string should return 422."""
        response = client.get(
            "/api/v1/overview",
            params={"start_date": "not-a-date"},
        )
        assert response.status_code == 422

    def test_nonexistent_channel_returns_404(self, client):
        """Filtering by a channel that doesn't exist should return 404."""
        response = client.get(
            "/api/v1/overview",
            params={"channel": "NonExistentChannel"},
        )
        assert response.status_code == 404

    def test_future_date_range_returns_404(self, client):
        """A date range with no data should return 404."""
        response = client.get(
            "/api/v1/trends",
            params={"start_date": "2099-01-01", "end_date": "2099-12-31"},
        )
        assert response.status_code == 404

    def test_nonexistent_endpoint_returns_404(self, client):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
