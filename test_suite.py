import pytest
import responses
import datetime
from APIAccess import *
from DebtFunctional import runDebtFunctional
from DebtObjectOriented import runDebtObjectOriented_LoadIds, runDebtObjectOriented_GenerateIds

# ====== Test Config ===============================================

config = {
    "RetryConnection": 3,
    "DateFormats": ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"],
    "URL": {
        "Debts": "https://my-json-server.typicode.com/druska/trueaccord-mock-payments-api/debts",
        "PaymentPlans": "https://my-json-server.typicode.com/druska/trueaccord-mock-payments-api/payment_plans",
        "Payments": "https://my-json-server.typicode.com/druska/trueaccord-mock-payments-api/payments"
    },
    "Tables": {
        "PaymentPlans": {
            "FrequencyToDays": {"WEEKLY": 7, "BI_WEEKLY": 14}
        }
    }
}

# ====== Mock data : Replica of Assesment data set =================

Debts = [
    {"amount": 123.46, "id": 0},
    {"amount": 100, "id": 1},
    {"amount": 4920.34, "id": 2},
    {"amount": 12938, "id": 3},
    {"amount": 9238.02, "id": 4}
]

PaymentPlans = [
    {"amount_to_pay": 102.5, "debt_id": 0, "id": 0, "installment_amount": 51.25, "installment_frequency": "WEEKLY",
     "start_date": "2020-09-28"},

    {"amount_to_pay": 100, "debt_id": 1, "id": 1, "installment_amount": 25, "installment_frequency": "WEEKLY",
     "start_date": "2020-08-01"},

    {"amount_to_pay": 4920.34, "debt_id": 2, "id": 2, "installment_amount": 1230.085,
     "installment_frequency": "BI_WEEKLY",
     "start_date": "2020-01-01"},

    {"amount_to_pay": 4312.67, "debt_id": 3, "id": 3, "installment_amount": 1230.085, "installment_frequency": "WEEKLY",
     "start_date": "2020-08-01"}
]

Payments = [
    {"amount": 51.25, "date": "2020-09-29", "payment_plan_id": 0},
    {"amount": 51.25, "date": "2020-10-29", "payment_plan_id": 0},
    {"amount": 25, "date": "2020-08-08", "payment_plan_id": 1},
    {"amount": 25, "date": "2020-08-08", "payment_plan_id": 1},
    {"amount": 4312.67, "date": "2020-08-08", "payment_plan_id": 2},
    {"amount": 1230.085, "date": "2020-08-01", "payment_plan_id": 3},
    {"amount": 1230.085, "date": "2020-08-08", "payment_plan_id": 3},
    {"amount": 1230.085, "date": "2020-08-15", "payment_plan_id": 3}
]


# ====== Test APIAccess ============================================

@pytest.mark.parametrize("status, error", [
    (100, "Continue"),
    (204, "No Content"),
    (205, "Reset Content"),
    (300, "Multiple Choice"),
    (301, "Moved Permanently"),
    (303, "See Other"),
    (400, "Bad Request"),
    (401, "Unauthorized"),
    (403, "Forbidden"),
    (404, "Not Found")
])
@responses.activate
def test_APIAccess_HTTPResponseStatus(capfd, status, error):
    """ Test HTTP error responses """
    # === Mock Responses
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json={'error': f'{error}'},
                  status=status)
    # === Assertions
    if status < 400:
        output = f"***ERROR*** Error fetching data from Debts for no params: http response error: {error}\n"
    else:
        output = f"***ERROR*** Error fetching data from Debts for no params: {status} Client Error: " \
                 f"{error} for url: https://my-json-server.typicode.com/druska/trueaccord-mock-payments-api/debts\n"

    runDebtFunctional(config, basic1extra2both3=3, test_run=True)
    out, err = capfd.readouterr()
    assert out == output


# ====== Test Functional and OOP implementation ============================================

def runImplementation(impl):
    if impl == "Functional":
        runDebtFunctional(config, basic1extra2both3=3, test_run=True)
    if impl == "OOP":
        runDebtObjectOriented_LoadIds(config, basic1extra2both3=3, test_run=True)


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_Regression_BaseCase(capfd, impl):
    """
    Test Functional and OOP implementation for both simple and extra info with full dataset as presented in assessment
    :param capfd: responses library passes this param to capture console output
    """
    APIAccess.Today = datetime.datetime(2021, 1, 28)
    # === Mock Responses
    # Debts no param query
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=Debts,
                  content_type="application/json")

    # Payment plans parametrized query
    for dbt in Debts:
        dbt_id = dbt['id']
        pmt_plans = [pp for pp in PaymentPlans if pp['debt_id'] == dbt_id]
        url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
        responses.add(responses.GET,
                      url,
                      json=pmt_plans,
                      content_type="application/json")

    # Payments parametrized query
    for pp in PaymentPlans:
        pp_id = pp['id']
        payments = [pmt for pmt in Payments if pmt['payment_plan_id'] == pp_id]
        url = config['URL']['Payments'] + f"?payment_plan_id={pp_id}"
        responses.add(responses.GET,
                      config['URL']['Payments'],
                      json=payments,
                      content_type="application/json")

    # === Assertions
    output = \
        "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True}, " \
        "{'amount': 100.0, 'id': 1, 'in_payment_plan': True}, " \
        "{'amount': 4920.34, 'id': 2, 'in_payment_plan': True}, " \
        "{'amount': 12938.0, 'id': 3, 'in_payment_plan': True}, " \
        "{'amount': 9238.02, 'id': 4, 'in_payment_plan': False}]\n" \
        "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True, 'remaining_amount': 20.959999999999994, " \
        "'next_payment_due_date': datetime.datetime(2021, 2, 1, 0, 0)}, " \
        "{'amount': 100.0, 'id': 1, 'in_payment_plan': True, 'remaining_amount': 50.0, " \
        "'next_payment_due_date': datetime.datetime(2021, 1, 30, 0, 0)}, " \
        "{'amount': 4920.34, 'id': 2, 'in_payment_plan': True, 'remaining_amount': 607.6700000000001, " \
        "'next_payment_due_date': datetime.datetime(2021, 2, 10, 0, 0)}, " \
        "{'amount': 12938.0, 'id': 3, 'in_payment_plan': True, 'remaining_amount': 9247.745000000003, " \
        "'next_payment_due_date': datetime.datetime(2021, 1, 30, 0, 0)}, " \
        "{'amount': 9238.02, 'id': 4, 'in_payment_plan': False, 'remaining_amount': 9238.02, " \
        "'next_payment_due_date': None}]\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_DebtIsPaidOff(capfd, impl):
    """
    Test Functional and OOP implementation for deb t which has been paid off
    :param capfd: responses library passes this param to capture console output
    """
    APIAccess.Today = datetime.datetime(2021, 1, 28)
    # === Mock Responses
    # Debts

    # for debt 0, payments total is 102.5
    dbt = Debts[0].copy()
    dbt['amount'] = 102.5

    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[dbt],
                  content_type="application/json")

    # Payment plans parametrized query
    dbt_id = 0
    pmt_plans = [pp for pp in PaymentPlans if pp['debt_id'] == dbt_id]
    url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
    responses.add(responses.GET,
                  url,
                  json=pmt_plans,
                  content_type="application/json")

    # Payments parametrized query
    for pp in PaymentPlans:
        pp_id = pp['id']
        payments = [pmt for pmt in Payments if pmt['payment_plan_id'] == pp_id]
        url = config['URL']['Payments'] + f"?payment_plan_id={pp_id}"
        responses.add(responses.GET,
                      config['URL']['Payments'],
                      json=payments,
                      content_type="application/json")

    # === Assertions
    output = \
        "[{'amount': 102.5, 'id': 0, 'in_payment_plan': True}]\n" \
        "[{'amount': 102.5, 'id': 0, 'in_payment_plan': True, 'remaining_amount': 0.0, " \
        "'next_payment_due_date': None}]\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output

@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_NoData_Debts(capfd, impl):
    """
    Test Functional and OOP implementation for missing Debts data
    :param capfd: responses library passes this param to capture console output
    """

    # === Mock Responses
    # Debts no param query
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[],
                  content_type="application/json")

    # === Assertions
    output = "[]\n[]\n"
    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_NoData_PaymentPlans(capfd, impl):
    """
    Test Functional and OOP implementation for missing PaymentPlans data
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts no param query
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=Debts,
                  content_type="application/json")

    # Payment plans parametrized query
    for dbt in Debts:
        dbt_id = dbt['id']
        dbt_plans = []
        url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
        responses.add(responses.GET,
                      url,
                      json=dbt_plans,
                      content_type="application/json")

    # === Assertions
    output = \
        "[{'amount': 123.46, 'id': 0, 'in_payment_plan': False}, " \
        "{'amount': 100.0, 'id': 1, 'in_payment_plan': False}, " \
        "{'amount': 4920.34, 'id': 2, 'in_payment_plan': False}, " \
        "{'amount': 12938.0, 'id': 3, 'in_payment_plan': False}, " \
        "{'amount': 9238.02, 'id': 4, 'in_payment_plan': False}]\n" \
        "[{'amount': 123.46, 'id': 0, 'in_payment_plan': False, 'remaining_amount': 123.46, " \
        "'next_payment_due_date': None}, " \
        "{'amount': 100.0, 'id': 1, 'in_payment_plan': False, 'remaining_amount': 100.0, " \
        "'next_payment_due_date': None}, " \
        "{'amount': 4920.34, 'id': 2, 'in_payment_plan': False, 'remaining_amount': 4920.34, " \
        "'next_payment_due_date': None}, " \
        "{'amount': 12938.0, 'id': 3, 'in_payment_plan': False, 'remaining_amount': 12938.0, " \
        "'next_payment_due_date': None}, " \
        "{'amount': 9238.02, 'id': 4, 'in_payment_plan': False, 'remaining_amount': 9238.02, " \
        "'next_payment_due_date': None}]\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_NoData_Payments(capfd, impl):
    """
    Test Functional and OOP implementation for missing Payments data
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts no param query
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=Debts,
                  content_type="application/json")

    # Payment plans parametrized query
    for dbt in Debts:
        dbt_id = dbt['id']
        dbt_plans = [pp for pp in PaymentPlans if pp['debt_id'] == dbt_id]
        url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
        responses.add(responses.GET,
                      url,
                      json=dbt_plans,
                      content_type="application/json")

    # Payments parametrized query
    for pp in PaymentPlans:
        pp_id = pp['id']
        payments = []
        url = config['URL']['Payments'] + f"?payment_plan_id={pp_id}"
        responses.add(responses.GET,
                      config['URL']['Payments'],
                      json=payments,
                      content_type="application/json")

    # === Assertions

    output = \
        "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True}, " \
        "{'amount': 100.0, 'id': 1, 'in_payment_plan': True}, " \
        "{'amount': 4920.34, 'id': 2, 'in_payment_plan': True}, " \
        "{'amount': 12938.0, 'id': 3, 'in_payment_plan': True}, " \
        "{'amount': 9238.02, 'id': 4, 'in_payment_plan': False}]\n" \
        "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True, 'remaining_amount': 123.46, " \
        "'next_payment_due_date': datetime.datetime(2021, 2, 1, 0, 0)}, " \
        "{'amount': 100.0, 'id': 1, 'in_payment_plan': True, 'remaining_amount': 100.0, " \
        "'next_payment_due_date': datetime.datetime(2021, 1, 30, 0, 0)}, " \
        "{'amount': 4920.34, 'id': 2, 'in_payment_plan': True, 'remaining_amount': 4920.34, " \
        "'next_payment_due_date': datetime.datetime(2021, 2, 10, 0, 0)}, " \
        "{'amount': 12938.0, 'id': 3, 'in_payment_plan': True, 'remaining_amount': 12938.0, " \
        "'next_payment_due_date': datetime.datetime(2021, 1, 30, 0, 0)}, " \
        "{'amount': 9238.02, 'id': 4, 'in_payment_plan': False, 'remaining_amount': 9238.02, " \
        "'next_payment_due_date': None}]\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_InvalidDebtAmount(capfd, impl):
    """
    Test Functional and OOP implementation for invalid debt amount
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts : return first debt record
    debt = {"amount": None, "id": 0}
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[debt],
                  content_type="application/json")

    # === Assertions
    output = "***ERROR*** Invalid debt amount : id=0 amount=None\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output

@responses.activate
def test_MultipleDebtIds_OOP(capfd):
    """
    Test OOP implementation for multiple debt ids
    This is the only test which uses runDebtObjectOriented_GenerateIds, which makes parametrized query to Debts API
    Functional implementation does not support generation of debt ids and querying Debts API one record at a time
    """
    # === Mock Responses
    # Debts : return first debt record
    url = config['URL']['PaymentPlans'] + f"?id={0}"
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[Debts[0], Debts[0]],
                  content_type="application/json")

    # === Assertions
    output = "***ERROR*** Corrupt debt data for debt_id '0' : multiple records\n"
    runDebtObjectOriented_GenerateIds(config, basic1extra2both3=3, test_run=True)
    out, err = capfd.readouterr()
    assert out == output

@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_MultiplePaymentPlans(capfd, impl):
    """
    Test Functional and OOP implementation for debt having multiple payment plans
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts : return first debt record
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[Debts[0]],
                  content_type="application/json")

    # Payment plans parametrized query
    dbt = Debts[0]
    dbt_id = dbt['id']
    multiple_pmt_plans = [PaymentPlans[0], PaymentPlans[1]]
    url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
    responses.add(responses.GET,
                  url,
                  json=multiple_pmt_plans,
                  content_type="application/json")

    # === Assertions
    output = "***ERROR*** Corrupt payment plan data for debt_id '0' : multiple records\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_InvalidPaymentPlanStartDate(capfd, impl):
    """
    Test Functional and OOP implementation for payment plan having invalid start date
    Payment plan start date is used only when no payments are made yet
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts : return first debt record
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[Debts[0]],
                  content_type="application/json")

    # Payment plans parametrized query
    dbt = Debts[0]
    dbt_id = dbt['id']
    pmt_plan = PaymentPlans[0].copy()
    pmt_plan['start_date'] = None
    url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
    responses.add(responses.GET,
                  url,
                  json=[pmt_plan],
                  content_type="application/json")

    # Payments parametrized query : no payments
    pp_id = pmt_plan['id']
    payments = []
    url = config['URL']['Payments'] + f"?payment_plan_id={pp_id}"
    responses.add(responses.GET,
                  config['URL']['Payments'],
                  json=payments,
                  content_type="application/json")

    # === Assertions
    output = "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True}]\n" \
             "***ERROR*** Start date for payment plan id '0' : invalid date value : 'None'\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_InvalidPaymentPlanInstallmentFrequency(capfd, impl):
    """
    Test Functional and OOP implementation for payment plan having invalid frequency
    Payment plan frequency is used only when some payments are made
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts no param query
    debt = Debts[0]
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[debt],
                  content_type="application/json")

    # Payment plans parametrized query
    dbt_id = debt['id']
    pmt_plan = PaymentPlans[dbt_id].copy()
    pmt_plan['installment_frequency'] = None
    url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
    responses.add(responses.GET,
                  url,
                  json=[pmt_plan],
                  content_type="application/json")

    # Payments parametrized query
    for pp in PaymentPlans:
        pp_id = pp['id']
        payments = [pmt for pmt in Payments if pmt['payment_plan_id'] == pp_id]
        url = config['URL']['Payments'] + f"?payment_plan_id={pp_id}"
        responses.add(responses.GET,
                      config['URL']['Payments'],
                      json=payments,
                      content_type="application/json")

    # === Assertions
    output = "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True}]\n" \
             "***ERROR*** Payment plan id '0 : unrecognized frequency 'None'\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output


@pytest.mark.parametrize("impl", ["Functional", "OOP"])
@responses.activate
def test_InvalidPaymentAmount(capfd, impl):
    """
    Test Functional and OOP implementation for payment having invalid amount
    :param capfd: responses library passes this param to capture console output
    """
    # === Mock Responses
    # Debts no param query
    debt = Debts[0]
    responses.add(responses.GET,
                  config['URL']['Debts'],
                  json=[debt],
                  content_type="application/json")

    # Payment plans parametrized query
    dbt_id = debt['id']
    pmt_plan = PaymentPlans[dbt_id]
    url = config['URL']['PaymentPlans'] + f"?debt_id={dbt_id}"
    responses.add(responses.GET,
                  url,
                  json=[pmt_plan],
                  content_type="application/json")

    # Payments parametrized query
    for pp in PaymentPlans:
        pp_id = pp['id']
        payments = [pmt.copy() for pmt in Payments if pmt['payment_plan_id'] == pp_id]
        payments[0]['amount'] = None
        url = config['URL']['Payments'] + f"?payment_plan_id={pp_id}"
        responses.add(responses.GET,
                      config['URL']['Payments'],
                      json=payments,
                      content_type="application/json")

    # === Assertions
    output = "[{'amount': 123.46, 'id': 0, 'in_payment_plan': True}]\n" \
             "***ERROR*** Invalid payment amount : amount=None, payment_plan_id=0,  date=2020-09-29\n"

    runImplementation(impl)
    out, err = capfd.readouterr()
    assert out == output

