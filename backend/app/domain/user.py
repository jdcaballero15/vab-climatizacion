from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    technician = "technician"
    owner = "owner"
