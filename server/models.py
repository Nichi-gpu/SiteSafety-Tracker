"""
SiteSafety Tracker - Backend Domain Models
===========================================
This module defines the Core Domain Entities and Object-Oriented representations
used across the SiteSafety Tracker application.

Each class encapsulates entity state, constructor initialization, business logic,
and serialization methods for SQLite database integration.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import bcrypt


class User:
    """
    Domain Entity representing an authenticated system user.
    
    Attributes:
        id (int): Unique identifier in the database.
        username (str): Handle / display username.
        email (str): Unique registered email address.
        role (str): Access level ('staff' or 'manager').
        company (str): Associated organization or division name.
        signup_time (str): Timestamp when account was created.
        last_login_time (str): Timestamp of the most recent login.
        login_count (int): Cumulative successful login count.
    """

    def __init__(
        self,
        username: str,
        email: str,
        role: str = 'staff',
        company: str = '',
        user_id: Optional[int] = None,
        signup_time: Optional[str] = None,
        last_login_time: Optional[str] = None,
        login_count: int = 0
    ):
        """
        Initializes a User entity instance.
        """
        self.id = user_id
        self.username = username.strip()
        self.email = email.strip().lower()
        self.role = role if role in ('staff', 'manager') else 'staff'
        self.company = company.strip()
        self.signup_time = signup_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.last_login_time = last_login_time
        self.login_count = login_count

    def is_manager(self) -> bool:
        """Returns True if user has administrative manager privileges."""
        return self.role == 'manager'

    def is_staff(self) -> bool:
        """Returns True if user is general reporting staff."""
        return self.role == 'staff'

    def to_dict(self) -> Dict[str, Any]:
        """Serializes user domain object into a clean dictionary (safe for JSON API output)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'company': self.company,
            'signup_time': self.signup_time,
            'last_login_time': self.last_login_time,
            'login_count': self.login_count
        }

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Generates a secure bcrypt salt and hash from a plain text password."""
        return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain text password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False


class HazardReport:
    """
    Domain Entity representing an on-site safety hazard incident.
    
    Attributes:
        ticket (str): Unique ticket identifier (e.g. ABC-2026-0923-42).
        location (str): Specific physical location or sector of the hazard.
        category (str): Hazard classification (e.g. Structural, Chemical, Electrical).
        date (str): Date when the incident was observed.
        time (str): Time when the incident was observed.
        urgency (str): Priority level ('Low', 'Medium', 'High', 'Critical').
        status (str): Workflow status ('Pending' or 'Resolved').
        cause (str): Narrative description and root cause of the hazard.
        photo (str): Base64 data URL or photo asset path.
        reporter (dict): Personnel contact information of the reporter.
        resolved_date (str): Date timestamp when marked as resolved.
    """

    def __init__(
        self,
        ticket: str,
        location: str,
        category: str,
        date: str,
        time: str,
        urgency: str = 'Medium',
        status: str = 'Pending',
        cause: str = '',
        photo: str = '',
        reporter: Optional[Dict[str, str]] = None,
        resolved_date: Optional[str] = None,
        report_id: Optional[int] = None
    ):
        """
        Initializes a HazardReport entity instance.
        """
        self.id = report_id
        self.ticket = ticket
        self.location = location
        self.category = category
        self.date = date
        self.time = time
        self.urgency = urgency
        self.status = status if status in ('Pending', 'Resolved') else 'Pending'
        self.cause = cause
        self.photo = photo
        self.reporter = reporter or {
            'name': 'Site Personnel',
            'position': 'Safety Officer',
            'phone': '+1 (555) 019-2834',
            'dept': 'Safety & Operations'
        }
        self.resolved_date = resolved_date

    def mark_resolved(self, resolution_date: Optional[str] = None) -> None:
        """Updates status to Resolved with resolution timestamp."""
        self.status = 'Resolved'
        self.resolved_date = resolution_date or datetime.now().strftime('%m-%d-%Y')

    def is_resolved(self) -> bool:
        """Checks if the hazard has been resolved."""
        return self.status == 'Resolved'

    def to_dict(self) -> Dict[str, Any]:
        """Serializes hazard record into a dictionary format matching UI contract."""
        return {
            'id': self.id,
            'ticket': self.ticket,
            'location': self.location,
            'category': self.category,
            'date': self.date,
            'time': self.time,
            'urgency': self.urgency,
            'status': self.status,
            'cause': self.cause,
            'photo': self.photo,
            'personnel': self.reporter,
            'resolvedDate': self.resolved_date,
            'timestamp': f"{self.date} | {self.time}"
        }


class Inspection:
    """
    Domain Entity representing a scheduled safety inspection.
    
    Attributes:
        title (str): Title or inspection focus (e.g. Scaffolding Rigidity Check).
        location (str): Site zone or building sector.
        inspector (str): Assigned certified inspector name.
        date (str): Scheduled inspection date.
        time (str): Scheduled inspection time.
        status (str): Inspection progress state ('Scheduled', 'Completed', 'In Progress').
    """

    def __init__(
        self,
        title: str,
        location: str,
        inspector: str,
        date: str,
        time: str,
        status: str = 'Scheduled',
        inspection_id: Optional[int] = None
    ):
        """
        Initializes an Inspection entity instance.
        """
        self.id = inspection_id
        self.title = title
        self.location = location
        self.inspector = inspector
        self.date = date
        self.time = time
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """Serializes inspection item into a dictionary for API delivery."""
        return {
            'id': self.id,
            'title': self.title,
            'location': self.location,
            'inspector': self.inspector,
            'date': self.date,
            'time': self.time,
            'status': self.status
        }


class NotificationAlert:
    """
    Domain Entity representing a system notification or audit alert.
    
    Attributes:
        title (str): Notification message text.
        time_label (str): Human readable time label (e.g. 'Just now', '5m ago').
        unread (bool): Whether notification is unread.
        user_id (int): Associated target user ID.
    """

    def __init__(
        self,
        title: str,
        time_label: str = 'Just now',
        unread: bool = True,
        user_id: Optional[int] = None,
        notification_id: Optional[int] = None
    ):
        self.id = notification_id
        self.title = title
        self.time_label = time_label
        self.unread = unread
        self.user_id = user_id

    def mark_as_read(self) -> None:
        """Marks notification as read."""
        self.unread = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes notification entity into JSON-ready dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'time': self.time_label,
            'unread': self.unread,
            'userId': self.user_id
        }
