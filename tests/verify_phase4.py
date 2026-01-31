
import unittest
from app.tools import get_service_price

class TestServicePricing(unittest.TestCase):
    def test_get_service_price_apk(self):
        """Test looking up APK price."""
        result = get_service_price.invoke({"service_type": "APK"})
        self.assertIn("APK Keuring", result)
        self.assertIn("€35.00", result)
        print(f"APK Price Output: {result}")

    def test_get_service_price_beurt(self):
        """Test looking up maintenance price (grote beurt)."""
        result = get_service_price.invoke({"service_type": "grote beurt"})
        self.assertIn("Grote Beurt", result)
        self.assertIn("€189.00", result)
        print(f"Grote Beurt Price Output: {result}")

    def test_get_service_price_not_found(self):
        """Test looking up non-existent service."""
        result = get_service_price.invoke({"service_type": "spaceship repair"})
        self.assertIn("Geen prijsinformatie gevonden", result)
        print(f"Not Found Output: {result}")

if __name__ == "__main__":
    unittest.main()
