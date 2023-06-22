import abc
import logging
from email.mime.text import MIMEText
from email.header import Header
from api import config
from api.domain import events
import aiosmtplib
import boto3
from jinja2 import Environment, FileSystemLoader
from botocore.exceptions import ClientError


class AbstractNotifications(abc.ABC):
    @abc.abstractmethod
    async def publish(self, destination, message):
        raise NotImplementedError

    @abc.abstractmethod
    async def render_template(self, template, **kwargs):
        raise NotImplementedError


class AbstractPushNotifications(abc.ABC):
    @abc.abstractmethod
    async def send(self, destination, message):
        raise NotImplementedError


class iOSPushNotifications(AbstractPushNotifications):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server = None

    # In heare you might have a class to handle iOS Push notification events.


class EmailAWSNotifications(AbstractNotifications):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # set up Amazon SES client here
        self.client = boto3.client("ses", region_name="us-west-1")

    async def send(self, destination, message):
        self.logger.info(f"Sending email to {destination}")
        if isinstance(message, events.OrderStatusChanged):
            await self._send_order_changed(destination, message)
        if isinstance(message, events.OrderCreated):
            await self._send_order_created(destination, message)

    async def render_template(self, template, **kwargs):
        env = Environment(loader=FileSystemLoader("api/templates"))
        template = env.get_template(template)
        return template.render(**kwargs)

    async def _send_order_changed(
        self, destination, message: events.OrderStatusChanged
    ):
        template_vars = {
            "status": message.status.value,
            "updated_at": message.updated_at,
            "order_items": message.order_items,
        }
        html_template = await self.render_template(
            "order_status_changed.html", **template_vars
        )

        try:
            response = self.client.send_email(
                Destination={
                    "ToAddresses": ["saggatpwn@gmail.com"],
                },
                Message={
                    "Body": {
                        "Html": {
                            "Charset": "UTF-8",
                            "Data": html_template,
                        },
                    },
                    "Subject": {
                        "Charset": "UTF-8",
                        "Data": f"Your order status is updated to {message.status}",
                    },
                },
                Source="marcoiurman@gmail.com",
            )
        except ClientError as e:
            self.logger.error(e.response["Error"]["Message"])
        else:
            self.logger.info(f"Email sent! Message ID: {response['MessageId']}")

    async def _send_order_created(
        self, destination, message: events.OrderCreated
    ):
        template_vars = {
            "status": message.status.value,
            "total_cost": message.total_cost,
            "consume_location": message.consume_location,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
            "order_items": message.order_items,
        }
        html_template = await self.render_template(
            "order_created.html", **template_vars
        )

        try:
            response = self.client.send_email(
                Destination={
                    "ToAddresses": [destination],
                },
                Message={
                    "Body": {
                        "Html": {"Charset": "UTF-8", "Data": html_template},
                    },
                    "Subject": {
                        "Charset": "UTF-8",
                        "Data": "Your order has been created",
                    },
                },
                Source="marcoiurman@gmail.com",
            )
        except ClientError as e:
            self.logger.error(e.response["Error"]["Message"])

    async def publish(self, destination, message):
        await self.send(destination, message)


class EmailLocalNotifications(AbstractNotifications):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # set up local SMTP server for MailHog
        self.client = aiosmtplib.SMTP(
            hostname=config.get_mailhog_host(), port=1025
        )

    async def send(self, destination, message):
        self.logger.info(f"Sending email to {destination}")
        if isinstance(message, events.OrderStatusChanged):
            await self._send_order_changed(destination, message)
        if isinstance(message, events.OrderCreated):
            await self._send_order_created(destination, message)

    async def render_template(self, template, **kwargs):
        env = Environment(loader=FileSystemLoader("api/templates"))
        template = env.get_template(template)
        return template.render(**kwargs)

    async def _send_order_changed(
        self, destination, message: events.OrderStatusChanged
    ):
        template_vars = {
            "status": message.status.value,
            "updated_at": message.updated_at,
            "order_items": message.order_items,
        }
        html_template = await self.render_template(
            "order_status_changed.html", **template_vars
        )

        # send email with MailHog here
        email_msg = MIMEText(html_template, "html", "utf-8")
        email_msg["Subject"] = Header(
            f"Your order status is updated to {message.status}"
        )
        email_msg["From"] = "test@example.com"
        email_msg["To"] = destination
        await self.client.connect()
        await self.client.send_message(email_msg)

    async def _send_order_created(
        self, destination, message: events.OrderCreated
    ):
        template_vars = {
            "status": message.status.value,
            "total_cost": message.total_cost,
            "consume_location": message.consume_location,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
            "order_items": message.order_items,
        }
        html_template = await self.render_template(
            "order_created.html", **template_vars
        )

        email_msg = MIMEText(html_template, "html", "utf-8")
        email_msg["Subject"] = Header("Your order has been created", "utf-8")
        email_msg["From"] = "test@example.com"
        email_msg["To"] = destination
        await self.client.connect()
        await self.client.send_message(email_msg)

    async def publish(self, destination, message):
        await self.send(destination, message)
