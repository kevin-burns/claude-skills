# Volunteer rota: spec

## User stories

1. As a volunteer, I want to sign up for a shift, so that the coordinator knows I am coming.
2. As a volunteer, I want to drop out of a shift I signed up for, so that the coordinator can find someone else.
3. As a volunteer, I want to swap my shift with another volunteer, so that I can change days without leaving a gap.
4. As the coordinator, I want to see today's rota with who is coming to each shift.
5. As the coordinator, I want to see the week ahead, so that I can spot gaps early.
6. As the coordinator, I want to be told when a shift falls below its minimum, so that I can fill it in time.
7. As a volunteer, I want a reminder the day before my shift.

## Implementation decisions

- Four layers: web pages, an API, a database, and an email adapter for outgoing messages.
- Each shift has a minimum number of volunteers, set by the coordinator.
- Email goes through the food bank's existing email provider, behind the adapter.

## Out of scope

- Payments, donations and stock.
