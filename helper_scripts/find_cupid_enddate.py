#!/usr/bin/env python3
from __future__ import annotations

import datetime

import cftime
import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--start-date",
    required=True,
    help="Starting date, format is YYYY-MM-DD.",
)
@click.option(
    "--stop_option",
    required=True,
    help="Unit to increment date by.",
)
@click.option(
    "--stop_n",
    required=True,
    help="Number of units (option) to increment date by.",
)
@click.option(
    "--calendar",
    required=True,
    help="Calendar type. See cftime calendar types for additional information.",
)
def find_enddate(start_date, stop_n, stop_option, calendar):
    # Process inputs
    year, month, day = (int(i) for i in start_date.split("-"))
    calendar_map = {"GREGORIAN": "proleptic_gregorian", "NO_LEAP": "noleap"}
    calendar = calendar_map[calendar]
    stop_n = int(stop_n)

    start_date = cftime.datetime(year, month, day, calendar=calendar)
    end_date = start_date

    # Catch edge cases
    if stop_option == "nmonths":
        if start_date.day > 27:
            raise ValueError(
                "CUPID_STARTDATE >= 28. No standard for resolving monthly increments starting at the end of a month.",
            )

    # Make modifications
    if stop_option == "nyears":
        end_year = start_date.year + stop_n
        # Check Feb edge case
        if start_date.month == 2 and start_date.day == 29:
            if cftime.is_leap_year(end_year, calendar=calendar):
                end_day = 29
            else:
                end_day = 28
        else:
            end_day = start_date.day
        end_date = cftime.datetime(
            end_year,
            start_date.month,
            end_day,
            calendar=calendar,
        )
    if stop_option == "nmonths":
        end_month = start_date.month + stop_n % 12
        end_year = start_date.year + stop_n // 12
        end_date = cftime.datetime(
            end_year,
            end_month,
            start_date.day,
            calendar=calendar,
        )
    if stop_option == "ndays":
        time_delta = datetime.timedelta(days=stop_n)
        end_date = end_date + time_delta

    print(end_date.strftime("%Y-%m-%d"))  # for the bash script to use


if __name__ == "__main__":
    find_enddate()
