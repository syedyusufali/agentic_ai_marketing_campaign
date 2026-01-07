"""
CDP Storage Layer

SQLite-based persistence for customers, events, and segments.
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path
from contextlib import contextmanager


class CDPStorage:
    """
    SQLite storage backend for the CDP.
    Handles customers, events, segments, and campaigns.
    """

    def __init__(self, db_path: str = "data/marketing_platform.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Customers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    email TEXT,
                    phone TEXT,
                    external_ids TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    age INTEGER,
                    gender TEXT,
                    location TEXT,
                    timezone TEXT,
                    total_purchases INTEGER DEFAULT 0,
                    total_revenue REAL DEFAULT 0.0,
                    average_order_value REAL DEFAULT 0.0,
                    purchase_frequency REAL DEFAULT 0.0,
                    days_since_last_purchase INTEGER,
                    email_opens INTEGER DEFAULT 0,
                    email_clicks INTEGER DEFAULT 0,
                    website_visits INTEGER DEFAULT 0,
                    last_active TEXT,
                    churn_risk_score REAL DEFAULT 0.0,
                    lifetime_value_score REAL DEFAULT 0.0,
                    engagement_score REAL DEFAULT 0.0,
                    conversion_probability REAL DEFAULT 0.0,
                    segments TEXT,
                    tags TEXT,
                    status TEXT DEFAULT 'prospect',
                    custom_attributes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status)")

            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    event_type TEXT,
                    event_name TEXT,
                    properties TEXT,
                    source TEXT,
                    campaign_id TEXT,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    referrer TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)

            # Create indexes for events
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_customer ON events(customer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_campaign ON events(campaign_id)")

            # Segments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS segments (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE,
                    description TEXT,
                    criteria TEXT,
                    customer_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Campaigns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    campaign_type TEXT,
                    status TEXT DEFAULT 'draft',
                    segment_ids TEXT,
                    content TEXT,
                    workflow TEXT,
                    schedule TEXT,
                    metrics TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    started_at TEXT,
                    completed_at TEXT
                )
            """)

            # Campaign executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaign_executions (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT,
                    customer_id TEXT,
                    channel TEXT,
                    status TEXT,
                    sent_at TEXT,
                    delivered_at TEXT,
                    opened_at TEXT,
                    clicked_at TEXT,
                    converted_at TEXT,
                    error TEXT,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)

    # Customer operations
    def save_customer(self, customer) -> None:
        """Save or update a customer"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = customer.to_dict()

            # Convert complex fields to JSON
            data["external_ids"] = json.dumps(data.get("external_ids", {}))
            data["segments"] = json.dumps(data.get("segments", []))
            data["tags"] = json.dumps(data.get("tags", []))
            data["custom_attributes"] = json.dumps(data.get("custom_attributes", {}))

            cursor.execute("""
                INSERT OR REPLACE INTO customers (
                    id, email, phone, external_ids, first_name, last_name,
                    age, gender, location, timezone, total_purchases, total_revenue,
                    average_order_value, purchase_frequency, days_since_last_purchase,
                    email_opens, email_clicks, website_visits, last_active,
                    churn_risk_score, lifetime_value_score, engagement_score,
                    conversion_probability, segments, tags, status, custom_attributes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["email"], data["phone"], data["external_ids"],
                data["first_name"], data["last_name"], data["age"], data["gender"],
                data["location"], data["timezone"], data["total_purchases"],
                data["total_revenue"], data["average_order_value"],
                data["purchase_frequency"], data["days_since_last_purchase"],
                data["email_opens"], data["email_clicks"], data["website_visits"],
                data["last_active"], data["churn_risk_score"],
                data["lifetime_value_score"], data["engagement_score"],
                data["conversion_probability"], data["segments"], data["tags"],
                data["status"], data["custom_attributes"],
                data["created_at"], data["updated_at"]
            ))

    def get_customer(self, customer_id: str):
        """Get customer by ID"""
        from .customer import CustomerProfile

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_customer(row)
            return None

    def get_customer_by_email(self, email: str):
        """Get customer by email"""
        from .customer import CustomerProfile

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE email = ?", (email,))
            row = cursor.fetchone()

            if row:
                return self._row_to_customer(row)
            return None

    def _row_to_customer(self, row):
        """Convert database row to CustomerProfile"""
        from .customer import CustomerProfile, CustomerStatus

        data = dict(row)
        data["external_ids"] = json.loads(data.get("external_ids") or "{}")
        data["segments"] = json.loads(data.get("segments") or "[]")
        data["tags"] = json.loads(data.get("tags") or "[]")
        data["custom_attributes"] = json.loads(data.get("custom_attributes") or "{}")

        if data.get("last_active"):
            data["last_active"] = datetime.fromisoformat(data["last_active"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("status"):
            data["status"] = CustomerStatus(data["status"])

        return CustomerProfile(**data)

    def delete_customer(self, customer_id: str) -> None:
        """Delete a customer"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))

    def search_customers(self, **criteria) -> List:
        """Search customers by criteria"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM customers WHERE 1=1"
            params = []

            for key, value in criteria.items():
                if key == "status":
                    query += f" AND status = ?"
                    params.append(value.value if hasattr(value, "value") else value)
                elif key == "min_revenue":
                    query += " AND total_revenue >= ?"
                    params.append(value)
                elif key == "max_churn_risk":
                    query += " AND churn_risk_score <= ?"
                    params.append(value)
                elif key == "min_engagement":
                    query += " AND engagement_score >= ?"
                    params.append(value)

            cursor.execute(query, params)
            return [self._row_to_customer(row) for row in cursor.fetchall()]

    def get_customers_in_segment(self, segment_name: str) -> List:
        """Get all customers in a segment"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM customers WHERE segments LIKE ?",
                (f'%"{segment_name}"%',)
            )
            return [self._row_to_customer(row) for row in cursor.fetchall()]

    def get_all_customers(self, limit: int = 1000, offset: int = 0) -> List:
        """Get all customers with pagination"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM customers ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [self._row_to_customer(row) for row in cursor.fetchall()]

    def count_customers(self) -> int:
        """Get total customer count"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            return cursor.fetchone()[0]

    # Event operations
    def save_event(self, event) -> None:
        """Save an event"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = event.to_dict()
            data["properties"] = json.dumps(data.get("properties", {}))

            cursor.execute("""
                INSERT INTO events (
                    id, customer_id, event_type, event_name, properties,
                    source, campaign_id, session_id, ip_address, user_agent,
                    referrer, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["customer_id"], data["event_type"],
                data["event_name"], data["properties"], data["source"],
                data["campaign_id"], data["session_id"], data["ip_address"],
                data["user_agent"], data["referrer"], data["timestamp"]
            ))

    def get_events(
        self,
        customer_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List:
        """Get events with filters"""
        from .events import Event, EventType

        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if customer_id:
                query += " AND customer_id = ?"
                params.append(customer_id)

            if event_type:
                event_type_str = event_type.value if hasattr(event_type, "value") else event_type
                query += " AND event_type = ?"
                params.append(event_type_str)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            events = []
            for row in cursor.fetchall():
                data = dict(row)
                data["properties"] = json.loads(data.get("properties") or "{}")
                data["event_type"] = EventType(data["event_type"])
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                events.append(Event(**data))

            return events

    def aggregate_events(
        self,
        event_type,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day"
    ) -> Dict[str, int]:
        """Aggregate events by time period"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # SQLite date functions for grouping
            date_format = {
                "hour": "%Y-%m-%d %H:00",
                "day": "%Y-%m-%d",
                "week": "%Y-%W",
                "month": "%Y-%m"
            }.get(group_by, "%Y-%m-%d")

            event_type_str = event_type.value if hasattr(event_type, "value") else event_type

            query = f"""
                SELECT strftime('{date_format}', timestamp) as period, COUNT(*) as count
                FROM events
                WHERE event_type = ?
            """
            params = [event_type_str]

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " GROUP BY period ORDER BY period"

            cursor.execute(query, params)
            return {row[0]: row[1] for row in cursor.fetchall()}

    # Segment operations
    def save_segment(self, segment) -> None:
        """Save a segment definition"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO segments (
                    id, name, description, criteria, customer_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                segment.id, segment.name, segment.description,
                json.dumps(segment.criteria), segment.customer_count,
                segment.created_at.isoformat() if segment.created_at else datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))

    def get_segment(self, segment_id: str):
        """Get segment by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM segments WHERE id = ?", (segment_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_segment(row)
            return None

    def get_segment_by_name(self, name: str):
        """Get segment by name"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM segments WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return self._row_to_segment(row)
            return None

    def _row_to_segment(self, row):
        """Convert row to segment object"""
        from models.segment import Segment
        data = dict(row)
        data["criteria"] = json.loads(data.get("criteria") or "{}")
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return Segment(**data)

    def get_all_segments(self) -> List:
        """Get all segments"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM segments ORDER BY name")
            return [self._row_to_segment(row) for row in cursor.fetchall()]

    # Campaign operations
    def save_campaign(self, campaign) -> None:
        """Save a campaign"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = campaign.to_dict()

            cursor.execute("""
                INSERT OR REPLACE INTO campaigns (
                    id, name, description, campaign_type, status, segment_ids,
                    content, workflow, schedule, metrics, created_at, updated_at,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["name"], data["description"],
                data["campaign_type"], data["status"],
                json.dumps(data.get("segment_ids", [])),
                json.dumps(data.get("content", {})),
                json.dumps(data.get("workflow", {})),
                json.dumps(data.get("schedule", {})),
                json.dumps(data.get("metrics", {})),
                data["created_at"], data["updated_at"],
                data.get("started_at"), data.get("completed_at")
            ))

    def get_campaign(self, campaign_id: str):
        """Get campaign by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_campaign(row)
            return None

    def _row_to_campaign(self, row):
        """Convert row to campaign object"""
        from campaigns.campaign import Campaign, CampaignStatus, CampaignType
        data = dict(row)
        data["segment_ids"] = json.loads(data.get("segment_ids") or "[]")
        data["content"] = json.loads(data.get("content") or "{}")
        data["workflow"] = json.loads(data.get("workflow") or "{}")
        data["schedule"] = json.loads(data.get("schedule") or "{}")
        data["metrics"] = json.loads(data.get("metrics") or "{}")
        if data.get("status"):
            data["status"] = CampaignStatus(data["status"])
        if data.get("campaign_type"):
            data["campaign_type"] = CampaignType(data["campaign_type"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return Campaign(**data)

    def get_all_campaigns(self, status: Optional[str] = None) -> List:
        """Get all campaigns"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM campaigns WHERE status = ? ORDER BY created_at DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
            return [self._row_to_campaign(row) for row in cursor.fetchall()]

    # Stats
    def get_stats(self) -> Dict[str, Any]:
        """Get platform statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) FROM customers")
            stats["total_customers"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events")
            stats["total_events"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM segments")
            stats["total_segments"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM campaigns")
            stats["total_campaigns"] = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(total_revenue) FROM customers")
            stats["total_revenue"] = cursor.fetchone()[0] or 0

            return stats
