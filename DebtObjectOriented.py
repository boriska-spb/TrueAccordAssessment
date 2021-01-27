import sys
import requests
import json
from datetime import datetime, timedelta
from functools import reduce
from APIAccess import APIAccess


# ###################################### CLASSES #########################################################

class DebtRecord:
    """ Encapsulates basic debt info : debt-id, debt-amount, in-payment-plan flag"""

    def __init__(self, api, debt_id, amount=None):
        """
        Init with debt id and optional amount.
        Load remaining data form API
        :param api: instance of APIAccess
        :param debt_id : debt id
        :param amount  : debt amount (optional)
        When amount is not provided, it is loaded from API.
        That allows to load debt info, one at a time, for generated debt ids
        If debt id is not found, marker exception APIAccess.XDebtIdNotFound is raised,
        which signals stop iteration over debt records in Debts API
        """
        self.id = debt_id
        self.amount = self.verifyDebtAmount(amount if amount is not None else self.fetchDebtAmount(api))
        self.in_payment_plan = None
        self.load(api)

    def __str__(self):
        # mimic enriched data from functional implementation for uniform testing
        return f"{{'amount': {self.amount}, 'id': {self.id}, 'in_payment_plan': {self.in_payment_plan}}}"

    def __repr__(self):
        return self.__str__()

    def verifyDebtAmount(self, amount) -> float:
        try:
            return float(amount)
        except Exception:
            raise Exception(f"Invalid debt amount : id={self.id} amount={amount}")

    def fetchDebtAmount(self, api) -> str:
        rs = api.fetchDebts(self.id)
        if len(rs) == 0: raise APIAccess.XDebtNotFound(self.id)
        if len(rs) > 1: raise Exception(f"Corrupt debt data for debt_id '{self.id}' : multiple records")
        return rs[0]['amount']

    def load(self, api):
        """ Load basic debt data"""

        # load payment plan data
        rs = api.fetchPaymentPlans(self.id)
        if len(rs) > 1: raise Exception(f"Corrupt payment plan data for debt_id '{self.id}' : multiple records")

        # *** in_payment_plan
        self.in_payment_plan = len(rs) > 0

    # ============= DebtRecord : display
    @classmethod
    def displayHeaders(cls) -> str:
        return "Id   Amount     Payment Plan"

    def display(self, headers=True) -> str:
        if headers:
            return f"id:{self.id}, amount:{self.amount}, " \
                   f"{'payment plan:yes' if self.in_payment_plan else 'payment plan:no'}"
        else:
            return f"{self.id:<4} {self.amount:<10.2f} {'yes' if self.in_payment_plan else 'no'}"


class DebtRecordExtra(DebtRecord):

    def __init__(self, api, debt_id, amount=None):
        """
        Init with debt id and optional amount.
        Load remaining data form API
        :param api:     instance of APIAccess
        :param debt_id: debt id
        :param amount:  debt amount (optional)
        When amount is not provided, it is loaded from API.
        That allows to load debt info, one at a time, for generated debt ids
        If debt id is not found, marker exception APIAccess.XDebtIdNotFound is raised,
        which signals stop iteration over debt records in Debts API
        """
        self.remaining_amount = None
        self.next_payment_due_date = None

        # super will call 'load' override for this class
        # load will initialize remaining_amount and next_payment_due_date
        super(DebtRecordExtra, self).__init__(api, debt_id, amount)

    def __str__(self):
        # mimic enriched data from functional implementation for uniform testing
        return f"{{'amount': {self.amount}, 'id': {self.id}, 'in_payment_plan': {self.in_payment_plan}, " \
               f"'remaining_amount': {self.remaining_amount}, " \
               f"'next_payment_due_date': {self.next_payment_due_date.__repr__()}}}"

    def __repr__(self):
        return self.__str__()

    # ============= DebtRecordExtra : load
    def load(self, api):
        """ Override of DebtRecord::load : Load extended debt info"""

        def parse_date(sdate, err_hdr="") -> datetime:
            """parse date : try all formats from config (ISO 8061 '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d' etc) """
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

        def payment_amount(pmt) -> float:
            """ Verify that payment data has valid amount and return amount as a float"""
            try:
                return float(pmt['amount'])
            except Exception:
                raise Exception(f"Invalid payment amount : amount={pmt['amount']}, "
                                f"payment_plan_id={pmt['payment_plan_id']},  date={pmt['date']}")

        def payment_date(pmt) -> datetime:
            """ Verify that payment has valid date and return date as datetime"""
            try:
                return parse_date(pmt['date'])
            except Exception:
                raise Exception(f"Invalid payment date : amount={pmt['amount']}, "
                                f"payment_plan_id={pmt['payment_plan_id']}, date={pmt['date']}")

        # load payment plan data
        rs = api.fetchPaymentPlans(self.id)
        if len(rs) > 1: raise Exception(f"Corrupt payment plan data for debt_id '{self.id}' : multiple records")

        # *** in_payment_plan
        self.in_payment_plan = len(rs) > 0

        # -- has payment plan, calculate from payments
        # remaining_amount  : principal
        # next payment date : None
        if not self.in_payment_plan:
            self.remaining_amount = self.amount

        # -- has payment plan, calculate from payments
        # remaining_amount
        # next payment date
        else:
            pp = rs[0]
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
            self.next_payment_due_date = pp_start_date + timedelta(periods_to_next_pmt * period)

            # *** remaining amount
            payments = api.fetchPayments(ppid)

            if len(payments) == 0:
                self.remaining_amount = self.amount
            else:
                self.remaining_amount = reduce(lambda acc, pmt: acc - payment_amount(pmt), payments, self.amount)

            # debt is paid off : next payment dues is None
            if self.remaining_amount == 0:
                self.next_payment_due_date = None


    # ============= DebtRecordExtra : display
    @classmethod
    def displayHeaders(cls) -> str:
        return "Id   Amount     Payment Plan  Remaining Amount  Next Payment Due"

    def display(self, headers=True) -> str:
        if headers:
            return f"id:{self.id}, amount:{self.amount}, " \
                   f"payment plan:{'yes' if self.in_payment_plan else 'no'}, " \
                   f"remaining amount:{'N/A' if self.remaining_amount is None else self.remaining_amount}, " \
                   f"next payment due:{'N/A' if self.next_payment_due_date is None else self.next_payment_due_date}"
        else:
            return f"{self.id:<4} {self.amount:<10.2f} {'yes' if self.in_payment_plan else 'no':<12}  " + \
                   (f"{'N/A':<16}  " if self.remaining_amount is None else f"{self.remaining_amount:<16.2f}  ") + \
                   ("N/A" if self.next_payment_due_date is None else f"{self.next_payment_due_date}")


# ###################################### RUN UTILITIES ###################################################

def runDebtObjectOriented_LoadIds(cfg, basic1extra2both3=3, test_run=False):
    """
    Load all debts in Debts table from API
    Print out list of debt info
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
        # load all debts
        api = APIAccess.Instance(cfg)
        debts = api.fetchDebts()

        # ==== Debt info with In-Payment-Plan flag
        if basic1extra2both3 == 1 or basic1extra2both3 == 3:
            debts_basic = [DebtRecord(api, dbt['id'], dbt['amount']) for dbt in debts]

            if test_run:
                print(debts_basic)
            else:
                for dbt in debts_basic:
                    print(dbt.display(False))

        # ==== Debt info with In-Payment-Plan flag, Remaining-Amount and Next-Payment-Due-Date
        if basic1extra2both3 == 2 or basic1extra2both3 == 3:
            debts_extra = [DebtRecordExtra(api, dbt['id'], dbt['amount']) for dbt in debts]

            if test_run:
                print(debts_extra)
            else:
                for dbt in debts_extra:
                    print(dbt.display(False))

    except Exception as err:
        print(f"***ERROR*** {err}")


def runDebtObjectOriented_GenerateIds(cfg, basic1extra2both3=3, test_run=False):
    """
        Generate sequential debt ids
        Load debt info for each id from API
        Print out list of debt info
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

        # ==== Debt info with In-Payment-Plan flag
        if basic1extra2both3 == 1 or basic1extra2both3 == 3:
            # iteration loop
            try:
                debt_id = 0
                while True:
                    dbt = DebtRecord(api, debt_id)
                    if test_run:
                        print(dbt)
                    else:
                        print(dbt.display(False))
                    debt_id += 1
            except APIAccess.XDebtIdNotFound:
                pass

        # ==== Debt info with In-Payment-Plan flag, Remaining-Amount and Next-Payment-Due-Date
        if basic1extra2both3 == 2 or basic1extra2both3 == 3:
            # iteration loop
            try:
                debt_id = 0
                while True:
                    dbt = DebtRecordExtra(api, debt_id)
                    if test_run:
                        print(dbt)
                    else:
                        print(dbt.display(False))
                    debt_id += 1
            except APIAccess.XDebtIdNotFound:
                pass

    except Exception as err:
        print(f"***ERROR*** {err}")


# ###################################### MAIN ############################################################

if __name__ == '__main__':

    def arg(argn, dflt) -> str:
        if len(sys.argv) <= argn:
            return dflt
        return dflt if sys.argv[argn] == '-' else sys.argv[argn]

    """ 
    Program arguments: 
    value '-' means use default setting
    :argument1 : path to config file or '-'. Optional. Defaults to "debt_config"
    :argument2 : run mode or '-'. Optional 
         (l)oad      : load all debts from Debts API
         (g)enerate] : genrate sequential debt ids, and load debts form API one at a time
    :argument3 : test mode ('test' or none). 
                 If test mode is specified, output produced will mimic data from API
                 This output format is expected by test suite
    """

    # -- read config : 1st arg
    cfg_path = arg(1, "debt_config")
    try:
        with open(cfg_path) as cfg_file:
            config = json.load(cfg_file)
    except Exception as err:
        raise SystemExit(f"Cannot open config file : {err}")

    # -- run mode : 2nd arg
    # 'load' or 'l'     : load all debt records from debt table upfront
    # 'generate' or 'g' : generate all debt ids, starting from 0
    run_mode = arg(2, "l")

    # -- test mode : 3rd arg
    # test : run in test mode
    test_run = sys.argv[3] == "test" if (len(sys.argv) > 3) else False

    if run_mode == "load" or run_mode == "l":
        if not test_run:
            print("Load " + "=" * 75)
            print(DebtRecord.displayHeaders())
        runDebtObjectOriented_LoadIds(config, 1, test_run)

        if not test_run:
            print("-" * 80)
            print(DebtRecordExtra.displayHeaders())
        runDebtObjectOriented_LoadIds(config, 2, test_run)

    elif run_mode == "generate" or run_mode == "g":
        if not test_run:
            print("Generate " + "=" * 71)
            print(DebtRecord.displayHeaders())
        runDebtObjectOriented_GenerateIds(config, 1, test_run)

        if not test_run:
            print("-" * 80)
            print(DebtRecordExtra.displayHeaders())
        runDebtObjectOriented_GenerateIds(config, 2, test_run)
    else:
        raise SystemExit(f"Incorrect run mode '{run_mode}'.Expected 'g' or 'l' ")
