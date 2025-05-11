# Jetlog Flight Importer Guide

This guide explains how to use the `jetlog://import?data=` URL scheme to import flight and person data directly into the Jetlog application. This is useful for integrating with other services, bulk importing, or creating custom import scripts.

## Table of Contents

1.  [Overview](#overview)
2.  [The Import URL](#the-import-url)
3.  [JSON Data Structure](#json-data-structure)
    *   [Top-Level Structure](#top-level-structure)
    *   [Flight Entry (`entries`)](#flight-entry-entries)
    *   [Person Entry (`people`)](#person-entry-people)
4.  [JSON Example](#json-example)
5.  [Steps to Import](#steps-to-import)
6.  [Important Notes](#important-notes)

## Overview

Jetlog supports a custom URL scheme `jetlog://` for various actions. The `import` action allows you to pass flight and associated person data as a URL-encoded JSON string. When you click or open such a link, Jetlog (if installed and registered to handle `jetlog://` URIs) will parse the data and attempt to import it.

## The Import URL

The basic structure of the import URL is:

`jetlog://import?data=<URL_ENCODED_JSON_STRING>`

Where:
*   `jetlog://`: The custom protocol for Jetlog.
*   `import`: The action to perform.
*   `?data=`: A query parameter indicating the start of the data payload.
*   `<URL_ENCODED_JSON_STRING>`: Your JSON data, which has been URL-encoded (also known as percent-encoded).

## JSON Data Structure

The data passed to the `data=` parameter must be a JSON object.

### Top-Level Structure

The JSON object should have two main keys:

*   `entries`: An array of flight log entries.
*   `people`: An array of person objects (pilots, crew, etc.). These people can then be referenced within the flight entries.

```json
{
  "entries": [   ],
  "people": [   ]
}
```

### Flight Entry (`entries`)

Each object in the `entries` array represents a single flight and has the following structure:

| Field                   | Type    | Required | Description                                                                 | Example                       |
| :---------------------- | :------ | :------- | :-------------------------------------------------------------------------- | :---------------------------- |
| `type`                  | String  | Yes      | Must be `"flight"`.                                                         | `"flight"`                    |
| `date`                  | String  | Yes      | Flight date in `YYYY-MM-DD` format.                                         | `"2025-05-04"`                |
| `flight_number`         | String  | No       | Flight number.                                                              | `"KL1234"`                    |
| `scheduled_off_blocks`  | String  | No       | Scheduled off-blocks time in `HH:MM` (zulu).  | `"00:00"`      |
| `registration`          | String  | No       | Aircraft registration.                                                      | `"PHNXA"`                     |
| `from`                  | String  | No      | ICAO code of departure airport.                                             | `"EDDF"`                      |
| `to`                    | String  | No      | ICAO code of arrival airport.                                               | `"EHAM"`                      |
| `off_blocks`            | String  | No      | Actual off-blocks time in `HH:MM` (zulu).                   | `"08:15"`                     |
| `airborne`              | String  | No      | Actual airborne time in `HH:MM` (zulu).                     | `"09:15"`                     |
| `touchdown`             | String  | No      | Actual touchdown time in `HH:MM` (zulu).                    | `"10:15"`                     |
| `on_blocks`             | String  | No      | Actual on-blocks time in `HH:MM` (zulu).                    | `"12:15"`                     |                 |
| `people`                | Array   | No       | Array of people objects associated with this flight.                      | `[{"ref_id": "EMP123", ...}]` |
| `takeoffs_and_landings` | Object  | No       | Details about takeoffs and landings.                                        | `{"takeoffs": 0, "landings": 1}`       |

**Flight `people` Object:**
Each object within the flight's `people` array:

| Field    | Type   | Required | Description                                     | Example    |
| :------- | :----- | :------- | :---------------------------------------------- | :--------- |
| `ref_id` | String | Yes      | References a `ref_id` from the top-level `people` array, or use `"SELF"` to reference yourself. | `"EMP123"` |
| `role`   | String | Yes      | Role of the person on this flight (e.g., PIC, CP, Purser). | `"PIC"`    |

**`takeoffs_and_landings` Object:**

| Field      | Type   | Required | Description                                  | Example  |
| :--------- | :----- | :------- | :------------------------------------------- | :------- |
| `takeoffs` | Number | Yes      | Number of takeoffs for this leg.             | `1`      |
| `landings` | Number | Yes      | Number of landings for this leg.             | `1`      |

#### NOTE 
Use `"SELF"` to add yourself to the flight.

### Person Entry (`people`)

Each object in the top-level `people` array defines a person who can be assigned to flights.

| Field             | Type   | Required | Description                                    | Example        |
| :---------------- | :----- | :------- | :--------------------------------------------- | :------------- |
| `ref_id`          | String | Yes      | Unique identifier for this person. Referenced by flights. When using `"SELF"` you are referecing yourself. | `"EMP12345"`   |
| `first_name`      | String | Yes      | Person's first name.                           | `"Alice"`      |
| `last_name`       | String | Yes      | Person's last name.                            | `"Anderson"`   |
| `default_role`    | String | No       | Default role if not specified elsewhere.       | `"PIC"`        |
| `employee_number` | String | No       | Employee number, if applicable. Can be omitted.| `"12345"`      |

#### Note
It is not necessery to include `"SELF"` in the people list. If you include yourself in the people list, your fields will get updated by the data provided.

## JSON Example

Here's a minimal example of a JSON payload to import one flight with two crew members:

```json
{
  "entries": [
    {
      "type": "flight",
      "date": "2025-12-10",
      "flight_number": "KL1023",
      "scheduled_off_blocks": "14:00",
      "registration": "PH-BXD",
      "from": "EHAM",
      "to": "EGLL",
      "off_blocks": "14:08",
      "airborne": "14:28",
      "touchdown": "14:55",
      "on_blocks": "15:05",
      "people": [
        {
          "ref_id": "SELF",
          "role": "PIC"
        },
        {
          "ref_id": "REF2",
          "role": "FO"
        },
        {
          "ref_id": "REF3",
          "role": "Purser"
        }
      ],
      "takeoffs_and_landings": {
        "takeoffs": 1,
        "landings": 1
      }
    }
  ],
  "people": [
    {
      "ref_id": "REF2",
      "first_name": "Fantas",
      "last_name": "Tico",
      "default_role": "FO",
      "employee_number": "00923"
    },
    {
      "ref_id": "REF3",
      "first_name": "Sally",
      "last_name": "Skyway",
      "default_role": "Purser",
      "employee_number": "01556"
    }
  ]
}
```

## Steps to Import

1.  **Prepare your JSON data:** Create a JSON string following the structure described above.
    *   Ensure all required fields are present.
    *   Validate your JSON (e.g., using an online validator).

2.  **URL-encode the JSON string:**
    Most programming languages have built-in functions for URL encoding (e.g., `encodeURIComponent()` in JavaScript, `urllib.parse.quote_plus()` in Python). You can also use online URL encoders.
    *Example (conceptual JavaScript):*
    ```javascript
    const jsonData = { /* your JSON object */ };
    const jsonString = JSON.stringify(jsonData);
    const encodedData = encodeURIComponent(jsonString);
    ```

3.  **Construct the full import link:**
    Prepend `jetlog://import?data=` to your URL-encoded JSON string.
    *Example:*
    
    [jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222025-12-10%22%2C%22flight_number%22%3A%22KL1023%22%2C%22scheduled_off_blocks%22%3A%2214%3A00%22%2C%22registration%22%3A%22PH-BXD%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22off_blocks%22%3A%2214%3A08%22%2C%22airborne%22%3A%2214%3A28%22%2C%22touchdown%22%3A%2214%3A55%22%2C%22on_blocks%22%3A%2215%3A05%22%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22SELF%22%2C%22role%22%3A%22PIC%22%7D%2C%7B%22ref_id%22%3A%22REF2%22%2C%22role%22%3A%22FO%22%7D%2C%7B%22ref_id%22%3A%22REF3%22%2C%22role%22%3A%22Purser%22%7D%5D%2C%22takeoffs_and_landings%22%3A%7B%22takeoffs%22%3A1%2C%22landings%22%3A1%7D%7D%5D%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22REF2%22%2C%22first_name%22%3A%22Fantas%22%2C%22last_name%22%3A%22Tico%22%2C%22default_role%22%3A%22FO%22%2C%22employee_number%22%3A%2200923%22%7D%2C%7B%22ref_id%22%3A%22REF3%22%2C%22first_name%22%3A%22Sally%22%2C%22last_name%22%3A%22Skyway%22%2C%22default_role%22%3A%22Purser%22%2C%22employee_number%22%3A%2201556%22%7D%5D%7D](jetlog://import?data=%7B%22entries%22%3A%5B%7B%22type%22%3A%22flight%22%2C%22date%22%3A%222025-12-10%22%2C%22flight_number%22%3A%22KL1023%22%2C%22scheduled_off_blocks%22%3A%2214%3A00%22%2C%22registration%22%3A%22PH-BXD%22%2C%22from%22%3A%22EHAM%22%2C%22to%22%3A%22EGLL%22%2C%22off_blocks%22%3A%2214%3A08%22%2C%22airborne%22%3A%2214%3A28%22%2C%22touchdown%22%3A%2214%3A55%22%2C%22on_blocks%22%3A%2215%3A05%22%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22SELF%22%2C%22role%22%3A%22PIC%22%7D%2C%7B%22ref_id%22%3A%22REF2%22%2C%22role%22%3A%22FO%22%7D%2C%7B%22ref_id%22%3A%22REF3%22%2C%22role%22%3A%22Purser%22%7D%5D%2C%22takeoffs_and_landings%22%3A%7B%22takeoffs%22%3A1%2C%22landings%22%3A1%7D%7D%5D%2C%22people%22%3A%5B%7B%22ref_id%22%3A%22REF2%22%2C%22first_name%22%3A%22Fantas%22%2C%22last_name%22%3A%22Tico%22%2C%22default_role%22%3A%22FO%22%2C%22employee_number%22%3A%2200923%22%7D%2C%7B%22ref_id%22%3A%22REF3%22%2C%22first_name%22%3A%22Sally%22%2C%22last_name%22%3A%22Skyway%22%2C%22default_role%22%3A%22Purser%22%2C%22employee_number%22%3A%2201556%22%7D%5D%7D)
    
    *(The above example is the URL-encoded version of the JSON example provided in the previous section.)*

4.  **Use the link:**
    *   You can embed this link in an HTML page: `<a href="your_jetlog_import_link">Import to Jetlog</a>`.
    *   Paste it into your browser's address bar.
    *   Use a command-line tool to open the URL (e.g., `xdg-open` on Linux, `open` on macOS, `start` on Windows).

    If Jetlog is correctly installed and its URL scheme handler is registered, the application should open and process the import data.

## Important Notes

*   **URL Length Limits:** Browsers and operating systems may have limits on the maximum length of a URL. For very large imports, this method might not be suitable. Consider splitting large imports into smaller chunks.

*   **Error Handling:** Jetlog will handle validation of the imported data. If there are errors (e.g., missing required fields, incorrect data types, unknown `ref_id`s), the import for the affected entries may fail or be partial and be shown to the user.

*   **Date and Time:**
    *   `date` is `YYYY-MM-DD`.
    *   `scheduled_off_blocks`,`off_blocks`, `airborne`, `touchdown`, `on_blocks` are `HH:MM` times assumed to be zulu to the flight date at the respective departure/arrival locations. 
*   **Existing Data:** The behavior when importing data that might conflict with existing entries (e.g., same flight number and date) depends on Jetlog's internal logic. It might update existing entries, create duplicates, or reject the import. 
*   **`ref_id` Uniqueness:** Ensure `ref_id` values in the `people` array are unique. These `ref_id`s are used to link people to flights.
