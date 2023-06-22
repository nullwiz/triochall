# Trio Challange - Technical design

## Overview

The task is to build an RESTful API for order management.

The main concepts to be tackled are classic to an ecommerce application: **users** (with different roles, manager and customer), **products** with different **variations** (not part of the aggregate, as the product can exist without a variation, Tea example), and **order** (which as well, the OrderLine is part of, the order cannot exist with it).

## Domain implementation details

#### Order flow

```
Waiting -> Preparation -> Ready -> Delivered
```

Users cant cancel orders that are ready, or have already been delivered.
Similarly, Managers cant update the status of orders that have already been delivered, cant move an order from delivered to ready.

They can, however, move them from Preparation to Waiting, but this is a design choice.

### Soft deletes

Products and Variations are soft deleted. This is to keep historical data which might be relevant for Analytics.

The rest of the resources could have been soft deleted too.

## Specifications

In essence, the API should support:

- Auth (JWT OAuth2 is used) with different roles.

Manager role:

- Customization for products and its variations
- Changing order status

Customer role:

- Places new orders
- Views the catalog
- Views details for a given order
- Cancel orders.

**Notifications** must be supported as well. As an example, notifications are sent when the order is created and the status changes.

As well, there is a Redis client available for sending messages to a pubsub queue.

## Technical design

Knowing that both consumers and managers might want to track changes in real time, a solution must be implemented to make sure we can integrate both external services (like push notification OPNs) and our own internal analytics, and for that, I have decided to go for a command/event approach, with it's own message bus for internal communication. Commands can generate events which are processed right after.

I used FastAPI because of it's OpenAPI specification which provides quick documentation and aswell provides a competitive advantage that other python frameworks in terms of speed.
Also validations are, if dealing with dataclasses or pydantic models, baked in.

A notification service which would fanout notifications to wherever its relevant could be the consumer and our CoffeShop API, the provider, given we have a queue to put those relevant messages on. In production, there is typically a service which manages these preferences and fans out notifications.

Right now, the application supports sending raw emails using smtp to a fake email provider locally, and AWS SES (Simple Email Service) which we would typically use in production.

I also implemented some common patterns to keep consistency between layers and ease of iteration in case we need to switch technologies.
Common to, but not exclusive to domain driven development:

- Bootstrapping the application
- Dependency injection (FastAPI)
- Unit of work pattern
- Repository pattern
- Factory pattern
- Command Query Responstability Segregation (catalog view)

I wont explain each one of the benefits, as these are common standards in software engineer that we could discuss later on.

## Endpoints

Endpoints can be accessed by going to http://localhost:5000/docs.

## Setup

Setup is typically done simply by running

```
make setup
```

Expects docker to be installed, and after these **all test should pass and we should have about 80% coverage** .
The default configuration is that products and variations are created as the challenge description describes.
There are also the following users:

```
manager@example.com / test
customer@example.com / test
```

By default it's expected to work with the local mailhog instance to mock notification testing.
At this point, do watch the video to get more context.

## Integrations

- Amazon SES
  In order yo use SES you need to change the environment variables in the docker image. Mainly, "NOTIFICATIONS_ENV" set to "production", but also
  boto3 will require your credentials, that right now are added to the compose but would typically come from the secrets manager or injected variables at runtime.
  These credentials are access keys in the AWS IAM console for a user, which you must create. You must also send validation emails for sender and receiver.

## General comments

. I did not realize the second instruction about opening a PR in the repo.
In a real application, these would have been incremental changes and not a single PR. I missed that!
. I do expect feedback :)
