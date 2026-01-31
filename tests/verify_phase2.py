
import unittest
from app.tools import schedule_appointment, AppointmentInput
from pydantic import ValidationError

class TestAppointment(unittest.TestCase):
    def test_schedule_appointment_success(self):
        """Test successful booking with all required fields including kenteken."""
        # Use .invoke() for LangChain tools
        result = schedule_appointment.invoke({
            "date_time": "2026-02-15 10:00",
            "description": "Test APK",
            "customer_name": "Test User",
            "phone_number": "0612345678",
            "kenteken": "AB-123-CD"
        })
        self.assertIn("Afspraak bevestigd", result)
        print(f"Tool output: {result}")

    def test_schedule_appointment_missing_kenteken(self):
        """Test that missing kenteken raises a validation error (simulating tool requirement)."""
        with self.assertRaises(ValidationError):
            AppointmentInput(
                date_time="2026-02-15 10:00",
                description="Test APK",
                customer_name="Test User",
                phone_number="0612345678"
                # Missing kenteken
            )

if __name__ == "__main__":
    unittest.main()
