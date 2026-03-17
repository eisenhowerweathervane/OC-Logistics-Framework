"""
Email Fetcher - Phase 3
Fetches DAT load alert emails via IMAP and processes them.
"""

import imaplib
import email
from email.header import decode_header
import sqlite3
import json
import time
from datetime import datetime
from typing import Optional

from config import EMAIL_CONFIG, DATABASE_PATH
from dat_email_parser import parse_load_email
from profitability_engine import score_load, DEFAULT_ASSUMPTIONS


class EmailFetcher:
    """IMAP email fetcher for DAT load alerts."""

    def __init__(self, config: dict = None):
        self.config = config or EMAIL_CONFIG
        self.mail = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to IMAP server."""
        if not self.config["email"] or not self.config["password"]:
            print("Error: Email credentials not configured in config.py")
            return False

        try:
            if self.config["use_ssl"]:
                self.mail = imaplib.IMAP4_SSL(
                    self.config["imap_server"],
                    self.config["imap_port"]
                )
            else:
                self.mail = imaplib.IMAP4(
                    self.config["imap_server"],
                    self.config["imap_port"]
                )

            self.mail.login(self.config["email"], self.config["password"])
            self.connected = True
            print(f"Connected to {self.config['imap_server']}")
            return True

        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass
        self.connected = False

    def fetch_new_emails(self, folder: str = "INBOX", mark_read: bool = True) -> list[dict]:
        """
        Fetch new (unread) DAT load alert emails.

        Returns list of email dicts with id, subject, sender, body.
        """
        if not self.connected:
            if not self.connect():
                return []

        emails = []

        try:
            self.mail.select(folder)

            # Build search criteria
            criteria = ["UNSEEN"]

            if self.config.get("filter_sender"):
                criteria.append(f'FROM "{self.config["filter_sender"]}"')

            if self.config.get("filter_subject"):
                criteria.append(f'SUBJECT "{self.config["filter_subject"]}"')

            search_str = " ".join(criteria)
            _, message_ids = self.mail.search(None, search_str)

            if not message_ids[0]:
                return []

            for msg_id in message_ids[0].split():
                try:
                    _, msg_data = self.mail.fetch(msg_id, "(RFC822)")
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)

                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    # Get sender
                    sender = msg.get("From", "")

                    # Get body text
                    body = self._get_email_body(msg)

                    # Get message ID for deduplication
                    email_id = msg.get("Message-ID", str(msg_id))

                    emails.append({
                        "id": email_id,
                        "subject": subject,
                        "sender": sender,
                        "body": body,
                        "received_at": msg.get("Date", ""),
                        "msg_id": msg_id
                    })

                    if mark_read:
                        self.mail.store(msg_id, "+FLAGS", "\\Seen")

                except Exception as e:
                    print(f"Error processing email {msg_id}: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching emails: {e}")

        return emails

    def _get_email_body(self, msg) -> str:
        """Extract plain text body from email message."""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = msg.get_payload()

        return body

    def process_email(self, email_data: dict, assumptions: dict = None) -> dict:
        """
        Process a single email: parse loads, score them, save to database.

        Returns summary of processing results.
        """
        config = assumptions or DEFAULT_ASSUMPTIONS

        # Parse loads from email body
        loads = parse_load_email(email_data["body"])

        if not loads:
            return {
                "email_id": email_data["id"],
                "status": "no_loads",
                "loads_found": 0,
                "loads_saved": 0
            }

        # Score each load
        scored_loads = []
        for load in loads:
            scored = score_load(load, assumptions=config)
            scored_loads.append(scored)

        # Save to database
        saved_count = 0
        conn = sqlite3.connect(DATABASE_PATH)

        try:
            # Log the email
            conn.execute("""
                INSERT OR IGNORE INTO email_log (email_id, subject, sender, received_at, loads_found, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                email_data["id"],
                email_data["subject"],
                email_data["sender"],
                email_data["received_at"],
                len(scored_loads),
                "processed"
            ))

            # Save each load
            for scored in scored_loads:
                try:
                    conn.execute("""
                        INSERT INTO loads (
                            email_id,
                            origin_city, origin_state, destination_city, destination_state,
                            rate_total, mileage, deadhead_miles, weight,
                            equipment_type, commodity, pickup_date, pickup_time_window,
                            delivery_date, delivery_time_window, broker_name, broker_mc_number,
                            contact_phone, contact_email, load_number, notes,
                            total_miles, total_cost, net_revenue, profit, margin_pct,
                            rpm, all_in_rpm, drive_hours, total_hours, profit_per_hour,
                            score, action, floor_rpm, warnings
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        email_data["id"],
                        scored["origin_city"], scored["origin_state"],
                        scored["destination_city"], scored["destination_state"],
                        scored["rate_total"], scored["mileage"],
                        scored["deadhead_miles"], scored["weight"],
                        scored["equipment_type"], scored["commodity"],
                        scored["pickup_date"], scored["pickup_time_window"],
                        scored["delivery_date"], scored["delivery_time_window"],
                        scored["broker_name"], scored["broker_mc_number"],
                        scored["contact_phone"], scored["contact_email"],
                        scored["load_number"], scored.get("notes", ""),
                        scored["total_miles"], scored["total_cost"],
                        scored["net_revenue"], scored["profit"], scored["margin_pct"],
                        scored["rpm"], scored["all_in_rpm"],
                        scored["drive_hours"], scored["total_hours"], scored["profit_per_hour"],
                        scored["score"], scored["action"], scored["floor_rpm"],
                        json.dumps(scored["warnings"])
                    ))
                    saved_count += 1
                except sqlite3.IntegrityError:
                    # Duplicate load, skip
                    pass

            conn.commit()

        finally:
            conn.close()

        return {
            "email_id": email_data["id"],
            "status": "processed",
            "loads_found": len(scored_loads),
            "loads_saved": saved_count,
            "duplicates": len(scored_loads) - saved_count
        }


def poll_emails(interval_seconds: int = 60, max_iterations: Optional[int] = None):
    """
    Poll for new emails continuously.

    Args:
        interval_seconds: Seconds between checks
        max_iterations: Max number of iterations (None = infinite)
    """
    fetcher = EmailFetcher()

    if not fetcher.connect():
        print("Failed to connect. Check your config.py settings.")
        return

    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking for new emails...")

            emails = fetcher.fetch_new_emails()

            if emails:
                print(f"Found {len(emails)} new email(s)")
                for email_data in emails:
                    result = fetcher.process_email(email_data)
                    print(f"  - {email_data['subject'][:50]}... → "
                          f"{result['loads_found']} loads, {result['loads_saved']} saved")
            else:
                print("No new emails")

            if max_iterations and iteration >= max_iterations:
                break

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nStopping email polling...")
    finally:
        fetcher.disconnect()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        print(f"Starting email polling (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        poll_emails(interval_seconds=interval)
    else:
        print("Email Fetcher - Phase 3")
        print("=" * 50)
        print()
        print("Usage:")
        print("  python3 email_fetcher.py poll [interval_seconds]")
        print()
        print("Before running, configure config.py with:")
        print("  - EMAIL_CONFIG['email'] = 'your@email.com'")
        print("  - EMAIL_CONFIG['password'] = 'your-app-password'")
        print("  - EMAIL_CONFIG['filter_subject'] = 'DAT Load Alert'")
        print()

        # Test connection
        print("Testing connection with current config...")
        fetcher = EmailFetcher()
        if fetcher.connect():
            print("✓ Connection successful!")
            fetcher.disconnect()
        else:
            print("✗ Connection failed. Check config.py")
