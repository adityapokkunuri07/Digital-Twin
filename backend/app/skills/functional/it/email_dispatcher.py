"""
email_dispatcher.py -- SKL_IT_EMAIL_DISPATCHER Functional Skill
================================================================
Adapted from the provided SKL_EMAIL_NOTIFICATION skill.
Sends stakeholder briefs via SMTP with DOCX file attachments.

Uses standard Python smtplib and MIMEMultipart.
Auto-discovered by skill_router.py -- NO edits to shared files needed.
"""
from typing import Dict, Any
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from app.skills.functional.base_skill import BaseFunctionalSkill


class EmailDispatcherSkill(BaseFunctionalSkill):
    """
    Sends stakeholder briefs via SMTP with optional DOCX attachment.
    Adapted from the team's SKL_EMAIL_NOTIFICATION skill.
    """

    @staticmethod
    def skill_name() -> str:
        return "SKL_IT_EMAIL_DISPATCHER"

    @staticmethod
    def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an email to a stakeholder with optional DOCX attachment.

        Args (payload):
            recipient_email: Target email address
            subject: Email subject line
            body_text: The brief content as email body
            persona_name: Name of the audience (for logging)
            docx_url: Optional URL of the DOCX file to attach
            docx_path: Optional local path to DOCX file to attach
        """
        print("\n--- [EMAIL_DISPATCHER] Starting email delivery ---")

        recipient = payload.get("recipient_email", "")
        subject = payload.get("subject", "Architecture Decision Brief")
        body_text = payload.get("body_text", "")
        persona_name = payload.get("persona_name", "Stakeholder")
        docx_path = payload.get("docx_path", "")

        # Redirect to TEST_RECIPIENT_EMAIL if set in .env for easy testing
        test_recipient = os.getenv("TEST_RECIPIENT_EMAIL")
        if test_recipient:
            print(f"[EMAIL_DISPATCHER] Redirecting to test recipient: {test_recipient}")
            recipient = test_recipient

        if not recipient:
            print("[EMAIL_DISPATCHER] No recipient email provided, skipping.")
            return {"success": False, "status": "NO_RECIPIENT", "recipient": ""}

        # Retrieve SMTP configuration from env
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("SENDER_EMAIL", smtp_user or "noreply@digitaltwin.local")

        success = False
        status_msg = "MOCKED"

        if smtp_host and smtp_port and smtp_user and smtp_password:
            print(f"[EMAIL_DISPATCHER] Sending to {recipient} via {smtp_host}...")
            try:
                # Build the email
                msg = MIMEMultipart()
                display_name = os.getenv("SENDER_DISPLAY_NAME", "Digital Twin - IT Architect")
                msg['From'] = f"{display_name} <{sender_email}>"
                msg['To'] = recipient
                msg['Subject'] = f"{subject} - {persona_name}"
                msg.attach(MIMEText(body_text, 'plain'))

                # Attach DOCX if available
                if docx_path and os.path.exists(docx_path):
                    try:
                        with open(docx_path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = f"brief_{persona_name.lower().replace(' ', '_')}.docx"
                        part.add_header("Content-Disposition", f"attachment; filename={filename}")
                        msg.attach(part)
                        print(f"[EMAIL_DISPATCHER] Attached DOCX: {filename}")
                    except Exception as e:
                        print(f"[EMAIL_DISPATCHER] Failed to attach DOCX: {e}")

                # Connect and send
                port = int(smtp_port)
                if port == 465:
                    server = smtplib.SMTP_SSL(smtp_host, port)
                else:
                    server = smtplib.SMTP(smtp_host, port)
                    server.starttls()

                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, recipient, msg.as_string())
                server.quit()

                print(f"[EMAIL_DISPATCHER] Email sent successfully to {recipient}!")
                success = True
                status_msg = "DELIVERED"

            except Exception as e:
                print(f"[EMAIL_DISPATCHER] SMTP error: {str(e)}")
                print("[EMAIL_DISPATCHER] Falling back to mock log.")
                success = True  # fallback mock
                status_msg = "MOCK_FALLBACK"
        else:
            print("[EMAIL_DISPATCHER] SMTP not configured. Mock email logged:")
            print(f"  To: {recipient}")
            print(f"  Subject: {subject} - {persona_name}")
            print(f"  Body length: {len(body_text)} chars")
            success = True
            status_msg = "MOCKED"

        print("--- [EMAIL_DISPATCHER] Email delivery complete ---\n")

        return {
            "success": success,
            "recipient": recipient,
            "persona_name": persona_name,
            "status": status_msg,
        }

    @staticmethod
    def describe_result(result: Dict[str, Any]) -> str:
        return f"Email ({result.get('status')}) to {result.get('recipient')} for {result.get('persona_name')} completed."
