Coding Assessment for Boris Ashman
mobile 646-244-6653

GITHUB REPOSITORY : https://github.com/boriska-spb/TrueAccordAssessment, branch Alt_NextPaymentDueDate


TASKS
======
1. Consume the HTTP API endpoints described below to create a script that will output debts, one JSON object per line, to stdout.
Each line should contain:
 - all of the debt's fields returned by the API
 - an additional boolean field, "is_in_payment_plan" set to true, if the debt is associated with a payment plan

2. Provide a test suite that validates the output being produced, along with any other operations performed internally

3 Add a new fields to the debts in the output:
 - remaining_amount, containing the calculated amount remaining to be paid on the debt. Output the value as a JSON number
 - next_payment_due_date", containing the ISO 8601 UTC date of when the next payment is due or
   null if there is no payment plan or if the debt has been paid off


DESIGN CONSIDERATIONS
=====================

Performance
-----------
Every call to API establishes new TCP session.
Reusing TCP session can provide performance improvement.
Limiting number of calls to API provides major performance improvement.

Memory
-----------
Limiting number of API calls implies loading bulk of data into memory.

1st option would be loading the whole database (Debts, PaymentPlans, Payments) into memory in 3 API calls.
It may significantly improve performance; however, it is quite unreasonable to assume that the whole database fits
into memory.

2nd option is loading all records in Debts table, then fetching required data per debt id from PaymentPlans and
Payments APIs. The assumption here is that all of the Debts table will fit into memory, which is moderately reasonable.

3rd option is querying API one debt id at a time.
That would be the slowest yet most memory-saving option.
It could become viable, if Debts table is too large to fit into memory.
The problem could be potentially solved by streaming APIs, but current API is REST-based and does not support
streaming requests. In order to implement one-record-at-a-time debt load, we need a rule to generate debt ids to
query Debts table. Judging by the available data in Assessment Debts table, debt ids form a sequence,
starting from 0 and incremented by 1. One may reasonably assume that this the sequence of auto-generated primary keys
and use this assumption to generate debt ids on client end programmatically.

In this assessment, I implemented 2nd and 3rd options.

Functional vs Object-Oriented
------------------------------
Functional approach is simple and efficient.
Object-oriented approach provides more flexibility and reusable classes which could be a part of the library.

In this assessment, I implemented both Functional and Object-Oriented approaches.
Given that ultimate purpose of this exercise is assessment of my coding skills, I thought it would be useful
to demonstrate my skills in both Functional and Object-Oriented approach.

Functional solution implements only 2nd option, i.e. loading all of the Debts table into memory and processing
debts one-by-one.
Objected-Oriented solution implements 2nd and, additionally, 3rd option - i.e. generate sequence of debt ids,
starting form zero and incremented by one, and load debt data by querying Debts table for generated id.
The iteration stops when debt id is not found in Debts table (i.e. empty data returned)


IMPLEMENTATION
===============

APIAccess.py
------------
Classes:
    APIAccess : a singleton object, encapsulating all queries to API.

    All requests are made via HTTP session object, which is reused between different API calls.
    Each API table has its own dedicated session object.


DebtFunctional.py
-----------------
Implements functional solution.
Load all debt data from Debts table and enrich it with additional data, produced off PaymentPlans and Payments data.

Functions:

    runDebtFunctional(cfg, basic1extra2both3=3, test_run=False)
    -----------------------------------------------------------
    Print 2 lists :
      list of debt basic info (id, amount, in-payment-plan)
      list of debt extended info (id, amount, in-payment-plan, remaining-amount, next-payment-due-date)
    Parameters
      cfg               : config dictionary
      basic1extra2both3 : 1 - print debts basic info only
                          2 - print extended info only,
                          3 - print both
      test_run          : True - print data as list of dictionaries, mimicking API data (used for unit test)
                          False - print data as tables with headers
    main
    -----
    Run solution
    Print both lists as tables with headers
    Arguments : path to config file (optional)
    Print both lists as tables with headers


DebtObjectOriented.py
---------------------
Implements Object-Oriented solution
Classes:
    DebtRecord      - encapsulates basic debt info (id, amount, in-payment-plan)
    DebtRecordExtra - encapsulates extended debt info (id, amount, in-payment-plan, remaining-amount, next-payment-due-date)

Functions:
    runDebtObjectOriented_LoadIds(cfg, basic1extra2both3, test_run)
    runDebtObjectOriented_GenerateIds(cfg, basic1extra2both3, test_run)

    Both function implement the same functionality as runDebtFunctional(cfg, basic1extra2both3=3, test_run=False)
    However, runDebtObjectOriented_LoadIds loads all debt ids form Debts API at once,
    while runDebtObjectOriented_GenerateIds loads one debt id at time for sequential ids.

    main
    -----
    Run solution
    Print both lists as tables with headers
    Has 3 positional arguments :
        - path to config file or '-'. Optional. Defaults to "debt_config"
        - run mode or '-'. Optional
            (l)oad      : load all debts from Debts API
            (g)enerate] : genrate sequential debt ids, and load debts form API one at a time
        - test mode ('test' or none).
            If test mode is specified, output produced will mimic data from API
            This output format is expected by test suite
    Any argument can be replaced with '-' to indicate that default setting should be used


test_suite.py
--------------
pytest-based test suite

debt_config
------------
Configuration file in JSON format


DEPENDENCIES
==============
Solution uses following packages
requests
responses
pytest

These packages must be installed on your system in order to run this solution

==================================================================================================================
==================================================================================================================

DEVELOPMENT PROCESS OVERVIEW

I had to combine work on this assessment with other activities, but that was fun.
High level overview of development by the dates is below.

Thursday, January 21
---------------------
I received assessment by noon, but was busy during the day and had a look at it only in the evening.
I looked at the data in the browser, and wrote a quick functional script as a proof of concept.
It produced desired output and used direct calls to API via requests.get.

I also thought of possible object-oriented implementation and tried to guess which one would be more appreciated.
Personally, I would go with Functional, but most of my experience as a developer was related to object-oriented
development in C++.
My understanding from initial phone conversation was that you use Scala as a main development platform.
Scala, on top of being fully functional, is amazingly well designed as an OO language (in my view,
many Scala OO features, like traits, variance specifications, type constructors etc, have the best of C++ spirit).

So I thought that you might appreciate OO solution as well, and decided that I have enough time to tackle both.
I ran a quick OO design and things-to-do for this assessment in my mind.


Friday, January 22
-------------------
Intermittently spent some time on assessment in the morning, and mostly in the evening.
Outlined major challenges and questions to clarify.
My major concern was, could the Debts table be too large to fit in the memory in real life.
If yes, what can done about it, given that API does not support streaming requests.
One possible solution was generate sequence of debt ids and load one record form Debts table at a time,
enriching it with data from PaymentPlans and Payments table per each debt_id.
I tried to clarify this question with Andre while working on development in the meantime.

Another question I had is about exact meaning of PaymentPlans.amount_to_pay,
which is described as "Total USD amount needed to be paid to resolve this debt".
My initial understanding was that this column would represent remaining amount under plan.
However, it was unclear why then the Problem Description mentioned that remained amount can be calculated from payments.
My first thought was that certain payments can be made on debts without the payment plan; but since Payments primary key
links to the PaymentPlans - not to the Debts table, all payments must be made only for debts under the payment plan.
I mailed Andrew this question as well, but in the meantime ran a quick check on available data - it turned out that
PaymentPlans.amount_to_pay doesn't match debt amount less total payments made.
So I rejected the assumption that PaymentPlans.amount_to_pay can be used to obtain remaining debt amount,
and that latter has to be calculated from payments.

In the meantime, I cleaned up functional solution a bit - encapsulated all API access in a dedicated object,
added checks for possible error conditions, rearranged the code.
By Friday night, functional solution took its final shape (more or less)

Saturday, January 23
--------------------
Worked on OO solution, mostly in the morning and a little bit in late afternoon.
For OO solution, I decided to implement both load options - load all records from Debts table at once,
and load one debt record at a time by programmatically generated debt id.
I factored the possibility for both approaches in classes' constructors implementation.
By the end of the Saturday, OO solution was pretty much ready.

Sunday, January 24
-------------------
Mostly, worked in the morning and in the evening.
First, I made a few minor changes to both solutions - polished output, added pretty print in table format and
fixed alignment.
Then, I focused on testing framework for HTTP API. Since it was somewhat unfamiliar topic for me,
I spent some time browsing the web and researching different approaches for mocking HTTP API.
I settled on the responses module, part of the requests package designed specifically to mock HTTP responses.
I also refreshed my knowledge about test packages and settled on pytest.

I also worked to compile the list of all relevant test scenarios.
My approach was to address a few areas :
- HTTP response status codes
- missing data
- all values which I check for error conditions in the code
- base case regression test, using available data in all 3 tables provided by API

I worked Sunday evening and late into the night, to implement most of test scenarios for functional solution.
Started with base case regression test, proceeded to missing data and invalid values, affecting the outcome.
In the process of implementing and running tests, I had to fix few minor bugs and make few changes
to functional solution, to better accommodate test calls and to provide more rigorous error checks.
By Saturday late night, test for functional solution was ready.

Monday, January 25
-------------------
In the morning, added test cases for HTTP status codes.
Made few mostly cosmetic changes to functional solution and tests.

Later in the day, worked to add OO solution to test suit - my preferred way was to use parametrized marks form pytest
(@pytest.mark.parametrize). I had to propagate the fixes I made to functional solution to the OO code,
rearrange and modify it so it could be seamlessly plugged in test infrastructure.
I also added a test specifically for OO solution using generated debt ids (this is the only case when I send
parametrized request to Debts table)

Then finally, reviewed the code, fixed comments here and there, made few largely cosmetic changes, ran test suit,
ran main functions in functional and OO solution to make sure everything is in place.

Then I wrote this note.

-------------------------
Thursday, January 28
After completing code for Scala solution, I realized I have to fix unit test-related bugs in Python solution as well.
I allowed to reset today's date affecting date calculations to provide compatibility with bac-dated
unit test data.


HOW COULD I HAVE DONE BETTER WITH MORE TIME
I think I used my time pretty efficiently, and it was fun. I enjoyed it.
One thing I should have done is to create git repo and check in my changes regularly - that would have saved
me some grace. As much more as this is exactly what has been advised in Assessment description.
It looks like I got too much focused on developing solution, at the expense of the process.

But I still have a time until deadline on Thursday - 2 days to be exact.
I intend to submit this solution, and work on similar Scala solution - if time permits.
This time, I would start with creating repo and checking in my code

One thing I would do when developing production code - spend more time clarifying the specs.
Email, of course, is not very efficient way, direct conversation is much better.
































