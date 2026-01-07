"""
Data Ingestion Module

Import customer and event data from various sources.
"""
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .customer import CustomerProfile, CustomerStatus
from .events import Event, EventType


class DataIngestion:
    """
    Data ingestion system for importing customers and events.
    Supports JSON, CSV, and programmatic data sources.
    """

    def __init__(self, storage):
        self.storage = storage
        self._import_stats = {
            "customers_imported": 0,
            "customers_updated": 0,
            "events_imported": 0,
            "errors": []
        }

    def reset_stats(self):
        """Reset import statistics"""
        self._import_stats = {
            "customers_imported": 0,
            "customers_updated": 0,
            "events_imported": 0,
            "errors": []
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get import statistics"""
        return self._import_stats.copy()

    def import_customers_json(self, file_path: str) -> Dict[str, Any]:
        """
        Import customers from JSON file.

        Expected format:
        [
            {
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                ...
            }
        ]
        """
        self.reset_stats()

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = [data]

            for item in data:
                self._import_customer(item)

        except Exception as e:
            self._import_stats["errors"].append(f"File error: {str(e)}")

        return self.get_stats()

    def import_customers_csv(self, file_path: str, mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Import customers from CSV file.

        Args:
            file_path: Path to CSV file
            mapping: Optional column name mapping, e.g., {"Email": "email", "Name": "first_name"}
        """
        self.reset_stats()
        mapping = mapping or {}

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Apply mapping
                    mapped_row = {}
                    for csv_col, value in row.items():
                        target_col = mapping.get(csv_col, csv_col.lower().replace(" ", "_"))
                        mapped_row[target_col] = value

                    self._import_customer(mapped_row)

        except Exception as e:
            self._import_stats["errors"].append(f"File error: {str(e)}")

        return self.get_stats()

    def _import_customer(self, data: Dict[str, Any]):
        """Import a single customer record"""
        try:
            # Check for existing customer by email
            email = data.get("email")
            existing = None
            if email:
                existing = self.storage.get_customer_by_email(email)

            # Parse numeric fields
            numeric_fields = [
                "age", "total_purchases", "total_revenue", "average_order_value",
                "purchase_frequency", "days_since_last_purchase", "email_opens",
                "email_clicks", "website_visits", "churn_risk_score",
                "lifetime_value_score", "engagement_score", "conversion_probability"
            ]
            for field in numeric_fields:
                if field in data and data[field]:
                    try:
                        if field in ["age", "total_purchases", "days_since_last_purchase",
                                     "email_opens", "email_clicks", "website_visits"]:
                            data[field] = int(data[field])
                        else:
                            data[field] = float(data[field])
                    except (ValueError, TypeError):
                        del data[field]

            # Parse list fields
            list_fields = ["segments", "tags"]
            for field in list_fields:
                if field in data and isinstance(data[field], str):
                    data[field] = [s.strip() for s in data[field].split(",") if s.strip()]

            # Parse status
            if "status" in data:
                try:
                    data["status"] = CustomerStatus(data["status"])
                except ValueError:
                    data["status"] = CustomerStatus.PROSPECT

            # Parse datetime fields
            datetime_fields = ["last_active", "created_at", "updated_at"]
            for field in datetime_fields:
                if field in data and isinstance(data[field], str):
                    try:
                        data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    except ValueError:
                        del data[field]

            if existing:
                # Update existing customer
                for key, value in data.items():
                    if value is not None and hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                self.storage.save_customer(existing)
                self._import_stats["customers_updated"] += 1
            else:
                # Create new customer
                profile = CustomerProfile(**data)
                self.storage.save_customer(profile)
                self._import_stats["customers_imported"] += 1

        except Exception as e:
            self._import_stats["errors"].append(f"Customer import error: {str(e)}")

    def import_events_json(self, file_path: str) -> Dict[str, Any]:
        """
        Import events from JSON file.

        Expected format:
        [
            {
                "customer_id": "xxx",
                "event_type": "purchase",
                "properties": {"revenue": 99.99},
                "timestamp": "2024-01-15T10:30:00"
            }
        ]
        """
        self.reset_stats()

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = [data]

            for item in data:
                self._import_event(item)

        except Exception as e:
            self._import_stats["errors"].append(f"File error: {str(e)}")

        return self.get_stats()

    def _import_event(self, data: Dict[str, Any]):
        """Import a single event record"""
        try:
            # Parse event type
            event_type_str = data.get("event_type", "custom")
            try:
                data["event_type"] = EventType(event_type_str)
            except ValueError:
                data["event_type"] = EventType.CUSTOM
                data["event_name"] = event_type_str

            # Parse timestamp
            if "timestamp" in data and isinstance(data["timestamp"], str):
                data["timestamp"] = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            else:
                data["timestamp"] = datetime.utcnow()

            # Ensure properties is a dict
            if "properties" not in data or not isinstance(data["properties"], dict):
                data["properties"] = {}

            event = Event(**data)
            self.storage.save_event(event)
            self._import_stats["events_imported"] += 1

        except Exception as e:
            self._import_stats["errors"].append(f"Event import error: {str(e)}")

    def import_from_dict(self, customers: List[Dict] = None, events: List[Dict] = None) -> Dict[str, Any]:
        """
        Import customers and events from dictionaries.

        Args:
            customers: List of customer dictionaries
            events: List of event dictionaries
        """
        self.reset_stats()

        if customers:
            for customer_data in customers:
                self._import_customer(customer_data)

        if events:
            for event_data in events:
                self._import_event(event_data)

        return self.get_stats()

    def generate_sample_data(self, num_customers: int = 100) -> Dict[str, Any]:
        """
        Generate sample customer and event data for testing.

        Args:
            num_customers: Number of sample customers to generate

        Returns:
            Import statistics
        """
        import random
        import string

        self.reset_stats()

        first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
                       "Isabella", "William", "Mia", "James", "Charlotte", "Alexander", "Amelia"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                      "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson"]
        locations = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
                     "San Antonio", "San Diego", "Dallas", "San Jose"]

        customers_created = []

        for i in range(num_customers):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"

            # Create customer with varied attributes
            customer_data = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "age": random.randint(18, 65),
                "location": random.choice(locations),
                "total_purchases": random.randint(0, 50),
                "total_revenue": round(random.uniform(0, 5000), 2),
                "email_opens": random.randint(0, 100),
                "email_clicks": random.randint(0, 50),
                "website_visits": random.randint(0, 200),
                "status": random.choice(list(CustomerStatus)).value,
            }

            # Calculate derived metrics
            if customer_data["total_purchases"] > 0:
                customer_data["average_order_value"] = round(
                    customer_data["total_revenue"] / customer_data["total_purchases"], 2
                )

            self._import_customer(customer_data)

            # Get the created customer for event generation
            created = self.storage.get_customer_by_email(email)
            if created:
                customers_created.append(created)

        # Generate events for customers
        event_types = [
            (EventType.PAGE_VIEW, 0.4),
            (EventType.PRODUCT_VIEW, 0.2),
            (EventType.ADD_TO_CART, 0.1),
            (EventType.PURCHASE, 0.1),
            (EventType.EMAIL_OPEN, 0.1),
            (EventType.EMAIL_CLICK, 0.1),
        ]

        for customer in customers_created:
            num_events = random.randint(1, 20)

            for _ in range(num_events):
                # Select random event type based on weights
                rand = random.random()
                cumulative = 0
                selected_type = EventType.PAGE_VIEW

                for event_type, weight in event_types:
                    cumulative += weight
                    if rand <= cumulative:
                        selected_type = event_type
                        break

                properties = {}
                if selected_type == EventType.PURCHASE:
                    properties["revenue"] = round(random.uniform(10, 500), 2)
                    properties["order_id"] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                elif selected_type == EventType.PRODUCT_VIEW:
                    properties["product_id"] = f"PROD-{random.randint(1000, 9999)}"
                    properties["category"] = random.choice(["Electronics", "Clothing", "Home", "Sports"])

                # Random timestamp in last 90 days
                days_ago = random.randint(0, 90)
                hours_ago = random.randint(0, 23)
                from datetime import timedelta
                timestamp = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)

                event_data = {
                    "customer_id": customer.id,
                    "event_type": selected_type,
                    "properties": properties,
                    "source": random.choice(["web", "mobile", "email"]),
                    "timestamp": timestamp,
                }

                self._import_event(event_data)

        return self.get_stats()
