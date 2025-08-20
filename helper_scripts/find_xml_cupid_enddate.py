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
    "--option",
    required=True,
    help="Unit to increment date by.",
)
@click.option(
    "--n",
    required=True,
    help="Number of units (option) to increment date by.",
)
@click.option(
    "--calendar",
    required=True,
    help="Calendar type. See cftime calendar types for additional information.",
)
def find_enddate(start_date, n, option, calendar):
    year, month, day = (int(i) for i in start_date.split("-"))
    start_date = cftime.datetime(year, month, day, calendar=calendar)
    end_date = start_date

    # Catch edge cases
    if option == "nyears" or option == "nmonths":
        if start_date.day != 1:
            raise ValueError(
                """If running with "nyears" or "nmonths" as CUPID_OPTION, the model run must begin on the
1st of the month. Otherwise use "ndays" (you might need to calculate the conversion yourself
if the calendar is uncommon).""",
            )

    # Make modifications
    if option == "nyears":
        end_year = start_date.year + n
        end_date = cftime.datetime(end_year, start_date.month, start_date.day)
    if option == "nmonths":
        end_month = start_date.month + n % 12
        end_year = start_date.year + n // 12
        end_date = cftime.datetime(end_year, end_month, start_date.day)
    if option == "ndays":
        time_delta = datetime.timedelta(days=n)
        end_date = end_date + time_delta

    return end_date


if __name__ == "__main__":

    end_date = find_enddate()

    print(end_date)  # for the bash script to use
