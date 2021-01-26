import requests
from functools import reduce


class APIAccess:
    """Encapsulates queries to Debts DB"""

    class XDebtIdNotFound(Exception):
        """
        Marker Exception XDebtIdNotFound is thrown when requested debt id is not present in Debts table
        Used as an indicator to stop iteration over Debts table via API calls
        """

    class APISession:
        """HTTP session to query Debts DB API"""

        def __init__(self, cfg, table):
            self.cfg = cfg
            self.table = table
            self.session = requests.Session()

        def httpRequest(self, request_params={}) -> list:
            """Generic HTTP GET request to API"""

            def err_msg():
                """Format error message """
                sparams = "no params" if len(request_params) == 0 \
                    else reduce(lambda acc, k: acc + f" {k}={request_params[k]}", request_params, " ")
                return f"Error fetching data from {self.table} for {sparams}"

            def check_error_response():
                # expect list of dict
                # error response : { 'error' : error-description }
                if type(data) is not list:
                    if type(data) is dict and 'error' in data:
                        raise Exception(f"{err_msg()}: http response error: {data['error']}")
                    else:
                        raise Exception(f"{err_msg()}: invalid http response {data}")

            # -- retry loop
            nretry = int(self.cfg['RetryConnection'])
            url = self.cfg['URL'][self.table]
            while True:
                nretry -= 1
                try:
                    rsp = self.session.get(url, params=request_params)
                    rsp.raise_for_status()
                    data = rsp.json()
                    check_error_response()

                    return data

                # timeout, connection error : retry until all retries exhausted
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
                    if nretry == 0:
                        raise Exception(f"{err_msg()}: {err}")

                # other errors
                except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
                    raise Exception(f"{err_msg()}: {err}")

    # ============= DBAccess instance
    _instance = None

    @classmethod
    def Instance(cls, cfg):
        if cls._instance is None:
            cls._instance = APIAccess(cfg)
        return cls._instance

    # ============= DBAccess methods
    def __init__(self, cfg):
        self.cfg = cfg
        self.sessionDebts = APIAccess.APISession(cfg, 'Debts')
        self.sessionPaymentPlans = APIAccess.APISession(cfg, 'PaymentPlans')
        self.sessionPayments = APIAccess.APISession(cfg, 'Payments')

    def fetchDebts(self, debt_id=None) -> list:
        """fetch data from Debts table, throws exception if failed"""
        parms = {} if debt_id is None else {'id': debt_id}
        debts = self.sessionDebts.httpRequest(parms)
        if debt_id is not None and len(debts) == 0 : raise APIAccess.XDebtIdNotFound
        return debts

    def fetchPaymentPlans(self, debt_id=None) -> list:
        """fetch data from Debts table, throws exception if failed"""
        parms = {} if debt_id is None else {'debt_id': debt_id}
        return self.sessionPaymentPlans.httpRequest(parms)

    def fetchPayments(self, payment_plan_id=None) -> list:
        """fetch data from Debts table, throws exception if failed"""
        parms = {} if payment_plan_id is None else {'payment_plan_id': payment_plan_id}
        return self.sessionPayments.httpRequest(parms)
