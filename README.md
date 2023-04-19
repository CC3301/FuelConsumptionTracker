# Fuel Consumption and Cost Monitoring via Telegram Bot

Create config.yaml (see config.yaml.example) and add bot_token and path to sqlite database location. Script will init db own it's own.


# Todo
Implement missing features:
    - Historical Data (possibly with graph generation?)
    - Detailed Information about Entries
    - Database stats maybe? (how many entries etc.)
    - Average Consumption across timerange

Implement "real" Database backend - SQlite is only for MVP

Implement some sort of identification system - limit access to certain people and allow sharing, maybe add something like per-car tracking?
