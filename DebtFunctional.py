import sys
import json
from datetime import datetime, timedelta
from functools import reduce
from APIAccess import APIAccess


def addInPaymentPlanFlag(api, debt_data) -> dict:
    """
    Calculate in-payment-plan flag
    Return enriched debt : {'in_payment_plan': True|False}
    """
    debt_id = debt_data['id']

    # make sure amount is float
    # update data type of amount in dictionary to float
    try:
        debt_data.update({'amount': float(debt_data['amount'])})
    except Exception:
        raise Exception(f"Invalid debt amount : id={debt_id} amount={debt_data['amount']}")

    plans = api.fetchPaymentPlans(debt_id)
    if len(plans) > 1: raise Exception(f"Corrupt payment plan data for debt_id '{debt_id}' : multiple records")
    return {'in_payment_plan': len(plans) > 0}


def addPaymentPlanExtraInfo(api, debt_data) -> dict:
    """
    Calculate in-payment-plan, remaining-amount, next-payment-due-date
    Returns enriched data { 'in_payment_plan':True|False, 'remaining_amount':float, 'next_payment_due_date':datetime}
    """

    def parse_date(sdate, err_hdr="") -> datetime:
        """Try all formats from config (ISO 8061 '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d' etc) """
        date_formats = api.cfg['DateFormats']
        for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d']:
            try:
                return datetime.strptime(sdate, fmt)
            except ValueError:
                continue
            # other errors, e.g date is None
            except Exception as err:
                raise Exception(f"{err_hdr} : invalid date value : '{sdate}'")

        raise Exception(f"{err_hdr} : unrecognized date format '{sdate}'")

    def payment_amount(pmt):
        """ Verify that payment has valid amount and return amount as float"""
        try:
            return float(pmt['amount'])
        except Exception:
            raise Exception(f"Invalid payment amount : amount={pmt['amount']}, "
                            f"payment_plan_id={pmt['payment_plan_id']},  date={pmt['date']}")

    def payment_date(pmt):
        """ Verify that payment has valid date and return date as datetime"""
        try:
            return parse_date(pmt['date'])
        except Exception:
            raise Exception(f"Invalid payment date : amount={pmt['amount']}, "
                            f"payment_plan_id={pmt['payment_plan_id']}, date={pmt['date']}")

    debt_id = debt_data['id']
    # verify debt amount
    try:
        debt_data.update({'amount': float(debt_data['amount'])})
    except Exception:
        raise Exception(f"Invalid debt amount : id={debt_id} amount={debt_data['amount']}")

    # fetch payment plan
    plans = api.fetchPaymentPlans(debt_id)
    if len(plans) > 1: raise Exception(f"Corrupt payment plan data for debt_id '{debt_id}' : multiple records")

    # --- debt has no payment plan
    if len(plans) == 0:
        return {'in_payment_plan': False,
                'remaining_amount': debt_data['amount'],
                'next_payment_due_date': None
                }

    # --- debt has payment plan
    pp = plans[0]
    ppid = pp['id']

    # payment plan start date
    pp_start_date = parse_date(pp['start_date'], f"Start date for payment plan id '{ppid}'")

    # installment frequency in days
    try:
        frequency = pp['installment_frequency']
        period = api.cfg["Tables"]["PaymentPlans"]["FrequencyToDays"][frequency]
    except KeyError:
        raise Exception(f"Payment plan id '{ppid} : unrecognized frequency '{frequency}'")

    # *** next payment due date : first date in payment schedule after or including today
    elapsed_days = (datetime.now() - pp_start_date).days
    periods_to_next_pmt = elapsed_days // period if elapsed_days % period == 0 else elapsed_days // period + 1
    next_payment_due_date = pp_start_date + timedelta(periods_to_next_pmt*period)

    payments = api.fetchPayments(ppid)

    # -- no payments yet made
    # *** remaining amount : principal
    # *** next pmt due date: pmt plan start date
    if len(payments) == 0:
        return {'in_payment_plan': True,
                'remaining_amount': debt_data['amount'],
                'next_payment_due_date': next_payment_due_date
                }

    # -- payments made

    # *** remaining amount
    remaining_amount = reduce(lambda acc, pmt: acc - payment_amount(pmt), payments, debt_data['amount'])
    if remaining_amount == 0:
        next_payment_due_date = None

    return {'in_payment_plan': True,
            'remaining_amount': remaining_amount,
            'next_payment_due_date': next_payment_due_date
            }


def runDebtFunctional(cfg, basic1extra2both3=3, test_run=False):
    """
    :param cfg : config dictionary
    :param basic1extra2both3
        1 : Output list of debts as : debt-id, amount, in-payment-plan
        2 : Output list of debts as : debt-id, amount, in-payment-plan, remaining-amount, next-payment-due-date
        3 : Output both
    :param test_run
        True  : print lists of dictionaries (for testing purposes)
        False : print lists as tables with headers
    """
    try:
        api = APIAccess.Instance(cfg)
        debts = api.fetchDebts()

        # ==== Debt info with In-Payment-Plan flag
        if basic1extra2both3 == 1 or basic1extra2both3 == 3:

            # add 'in_pmt_plan' flag to each debt in list
            debts_info = [dict(**dbt, **addInPaymentPlanFlag(api, dbt)) for dbt in debts]

            if test_run:
                print(debts_info)
            else:
                print("Id   Amount     Payment Plan")
                for dbt in debts_info:
                    print(f"{dbt['id']:<4} {dbt['amount']:<10.2f} {'yes' if dbt['in_payment_plan'] else 'no'}")

        # ==== Debt info with In-Payment-Plan flag, Remaining-Amount and Next-Payment-Due-Date
        if basic1extra2both3 == 2 or basic1extra2both3 == 3:

            # add 'in_pmt_plan', 'remaining_amount' and 'next_payment_due_date' to each debt in list
            debts_extra_info = [dict(**dbt, **addPaymentPlanExtraInfo(api, dbt)) for dbt in debts]

            if test_run:
                print(debts_extra_info)
            else:
                print('-' * 80)
                print("Id   Amount     Payment Plan  Remaining Amount  Next Payment Due")
                for dbt in debts_extra_info:
                    print(f"{dbt['id']:<4} {dbt['amount']:<10.2f} {'yes' if dbt['in_payment_plan'] else 'no':<12}  " + \
                          (f"{'N/A':<16}  " if dbt[
                                                   'remaining_amount'] is None else f"{dbt['remaining_amount']:<16.2f}  ") + \
                          ("N/A" if dbt['next_payment_due_date'] is None else f"{dbt['next_payment_due_date']}"))

    except Exception as err:
        print(f"***ERROR*** {err}")


# ###################################### MAIN ############################################################

if __name__ == '__main__':
    # -- read config : 1st arg
    cfg_path = sys.argv[1] if (len(sys.argv) > 1) else "debt_config"

    try:
        with open(cfg_path) as cfg_file:
            cfg = json.load(cfg_file)
    except Exception as err:
        raise SystemExit(f"Cannot open config file : {err}")

    # print both debt lists as tables
    runDebtFunctional(cfg, 3, False)  # True)
