"""
Custom exceptions for the application.
"""


class ApplicationException(Exception):
    """Base exception for the application."""
    
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


# Event exceptions
class EventNotFound(ApplicationException):
    def __init__(self):
        super().__init__("Event not found", "EVENT_NOT_FOUND", 404)


# Hold exceptions
class HoldNotFound(ApplicationException):
    def __init__(self):
        super().__init__("Hold not found", "HOLD_NOT_FOUND", 404)


class SeatsUnavailable(ApplicationException):
    def __init__(self):
        super().__init__("Not enough seats available", "SEATS_UNAVAILABLE", 409)


class HoldExpired(ApplicationException):
    def __init__(self):
        super().__init__("Hold has expired", "HOLD_EXPIRED", 409)


class InvalidSeatCount(ApplicationException):
    def __init__(self):
        super().__init__("Seat count must be positive", "INVALID_SEAT_COUNT", 400)


# Booking exceptions
class BookingNotFound(ApplicationException):
    def __init__(self):
        super().__init__("Booking not found", "BOOKING_NOT_FOUND", 404)


class DuplicateBooking(ApplicationException):
    def __init__(self):
        super().__init__("User already has confirmed booking for this event", "DUPLICATE_BOOKING", 409)


class InvalidHoldStatus(ApplicationException):
    def __init__(self):
        super().__init__("Hold status is invalid for confirmation", "INVALID_HOLD_STATUS", 409)


class BookingAlreadyCanceled(ApplicationException):
    def __init__(self):
        super().__init__("Booking already canceled", "BOOKING_ALREADY_CANCELED", 409)
